from app.adapters.llm.embedder import Embedder
from app.adapters.llm.reranker import Reranker
from app.adapters.retrieval.bm25_index import BM25Index
from app.adapters.retrieval.rrf_fuser import fuse_ranked_lists_with_scores
from app.adapters.storage.chroma_repo import ChromaRepo
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.core.config import Settings
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy


class RetrievalService:
    def __init__(
        self,
        settings: Settings,
        policy: RetrievalPolicy,
        sqlite_repo: SQLiteRepo,
        bm25_index: BM25Index,
        reranker: Reranker,
        embedder: Embedder,
        chroma_repo: ChromaRepo,
    ) -> None:
        self._settings = settings
        self._policy = policy
        self._sqlite_repo = sqlite_repo
        self._bm25_index = bm25_index
        self._reranker = reranker
        self._embedder = embedder
        self._chroma_repo = chroma_repo

    @property
    def settings(self) -> Settings:
        return self._settings

    async def retrieve(self, query: str) -> RetrievalBundle:
        return await self.retrieve_with_mode(query=query, mode="hybrid")

    async def retrieve_with_mode(
        self,
        query: str,
        mode: str = "hybrid",
        document_id: str | None = None,
        profile: str = "balanced",
    ) -> RetrievalBundle:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"hybrid", "bm25", "vector"}:
            normalized_mode = "hybrid"
        normalized_profile = profile.strip().lower()
        if normalized_profile not in {"fast", "balanced", "precision"}:
            normalized_profile = "balanced"
        target_document_id = document_id.strip() if document_id and document_id.strip() else None
        profile_config = self._profile_config(normalized_profile)

        active_chunks = self._sqlite_repo.list_active_chunks(document_id=target_document_id)
        bm25_hits = await self._bm25_index.search(
            query=query,
            chunks=active_chunks,
            limit=profile_config["bm25_k"],
        )

        vector_hits: list[dict[str, object]] = []
        vector_enabled = self._settings.retrieval_enable_vector and self._chroma_repo.is_available()
        embed_backend = "disabled"
        if vector_enabled and normalized_mode in {"hybrid", "vector"}:
            query_embedding = (await self._embedder.embed([query]))[0]
            embed_backend = self._embedder.last_backend
            vector_hits = await self._chroma_repo.query(
                query_embedding=query_embedding,
                limit=profile_config["vector_k"],
                document_id=target_document_id,
            )

        bm25_ranked_ids = [hit.chunk_id for hit in bm25_hits]
        vector_ranked_ids = [str(hit["id"]) for hit in vector_hits if hit.get("id")]
        vector_score_map = {str(hit["id"]): float(hit.get("score", 0.0)) for hit in vector_hits if hit.get("id")}
        bm25_score_map = {hit.chunk_id: hit.score for hit in bm25_hits}
        if normalized_mode == "bm25":
            top_bm25_score = max((hit.score for hit in bm25_hits), default=1.0)
            fused = [
                (chunk_id, min(1.0, bm25_score_map.get(chunk_id, 0.0) / max(top_bm25_score, 1e-9)))
                for chunk_id in bm25_ranked_ids
            ]
        elif normalized_mode == "vector":
            fused = [(chunk_id, vector_score_map.get(chunk_id, 0.0)) for chunk_id in vector_ranked_ids]
        else:
            fused = fuse_ranked_lists_with_scores(
                [bm25_ranked_ids, vector_ranked_ids],
                k=self._policy.rrf_k,
            )

        candidate_ids = [chunk_id for chunk_id, _ in fused[: profile_config["fused_k"]]]
        document_scope_fallback = False
        if target_document_id and not candidate_ids and active_chunks:
            candidate_ids = [str(chunk["id"]) for chunk in active_chunks[: profile_config["fused_k"]]]
            document_scope_fallback = True
        chunks_by_id = self._sqlite_repo.get_chunks_by_ids(candidate_ids)
        active_chunk_ids = {str(chunk["id"]) for chunk in active_chunks}
        orphan_vector_hit_count = len([chunk_id for chunk_id in vector_ranked_ids if chunk_id not in active_chunk_ids])
        candidate_ids = [chunk_id for chunk_id in candidate_ids if chunk_id in chunks_by_id]

        candidate_texts = [str(chunks_by_id[cid]["text"]) for cid in candidate_ids if cid in chunks_by_id]
        reranked_order = await self._reranker.rerank(query=query, texts=candidate_texts)
        rerank_backend = self._reranker.last_backend
        ordered_candidates = [candidate_ids[idx] for idx in reranked_order if idx < len(candidate_ids)]
        top_ids: list[str] = []
        per_document_counts: dict[str, int] = {}
        max_chunks_for_document = (
            profile_config["rerank_k"] if target_document_id else profile_config["max_chunks_per_document"]
        )
        for chunk_id in ordered_candidates:
            row = chunks_by_id.get(chunk_id)
            if not row:
                continue
            document_id = str(row["document_id"])
            current_count = per_document_counts.get(document_id, 0)
            if current_count >= max_chunks_for_document:
                continue
            top_ids.append(chunk_id)
            per_document_counts[document_id] = current_count + 1
            if len(top_ids) >= profile_config["rerank_k"]:
                break

        fused_score_map = {chunk_id: score for chunk_id, score in fused}

        chunks: list[RetrievedChunk] = []
        for chunk_id in top_ids:
            row = chunks_by_id.get(chunk_id)
            if not row:
                continue
            fused_score = fused_score_map.get(chunk_id, 0.0)
            lexical_score = bm25_score_map.get(chunk_id, 0.0)
            semantic_score = vector_score_map.get(chunk_id, 0.0)
            quality_score = self._normalize_quality(row.get("quality_score"))
            base_score = (0.5 * fused_score) + (0.3 * lexical_score) + (0.2 * semantic_score)
            quality_multiplier = 0.55 + (0.45 * quality_score)
            combined = base_score * quality_multiplier
            source = "hybrid"
            if chunk_id in bm25_score_map and chunk_id not in vector_score_map:
                source = "bm25"
            elif chunk_id in vector_score_map and chunk_id not in bm25_score_map:
                source = "vector"
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(row["document_id"]),
                    text=str(row["text"]),
                    score=combined,
                    page_start=int(row["page_start"]) if row["page_start"] is not None else None,
                    page_end=int(row["page_end"]) if row["page_end"] is not None else None,
                    source=source,
                    quality_score=quality_score,
                )
            )
        avg_quality = (
            round(sum(chunk.quality_score for chunk in chunks) / len(chunks), 3)
            if chunks
            else 0.0
        )

        return RetrievalBundle(
            chunks=chunks,
            meta={
                "bm25_k": self._policy.bm25_k,
                "vector_k": self._policy.vector_k,
                "fused_k": self._policy.fused_k,
                "profile_bm25_k": profile_config["bm25_k"],
                "profile_vector_k": profile_config["vector_k"],
                "profile_fused_k": profile_config["fused_k"],
                "rerank_k": profile_config["rerank_k"],
                "rrf_k": self._policy.rrf_k,
                "retrieved_count": len(chunks),
                "bm25_hits": len(bm25_hits),
                "vector_hits": len(vector_hits),
                "orphan_vector_hits_dropped": orphan_vector_hit_count,
                "vector_enabled": vector_enabled,
                "embed_backend": embed_backend,
                "rerank_backend": rerank_backend,
                "max_chunks_per_document": max_chunks_for_document,
                "diverse_documents": len(per_document_counts),
                "document_scope": target_document_id,
                "document_scope_fallback": document_scope_fallback,
                "average_chunk_quality": avg_quality,
                "quality_weighting": "enabled",
                "scope": "document" if target_document_id else "corpus",
                "retrieval_profile": normalized_profile,
                "strategy": f"phase1_{normalized_mode}",
            },
        )

    @staticmethod
    def _normalize_quality(value: object) -> float:
        try:
            quality = float(value)
        except (TypeError, ValueError):
            return 1.0
        return min(1.0, max(0.0, quality))

    def _profile_config(self, profile: str) -> dict[str, int]:
        if profile == "fast":
            return {
                "bm25_k": max(6, self._policy.bm25_k // 2),
                "vector_k": max(6, self._policy.vector_k // 2),
                "fused_k": max(8, self._policy.fused_k // 2),
                "rerank_k": max(4, self._policy.rerank_k // 2),
                "max_chunks_per_document": self._policy.max_chunks_per_document,
            }
        if profile == "precision":
            return {
                "bm25_k": max(self._policy.bm25_k, 32),
                "vector_k": max(self._policy.vector_k, 32),
                "fused_k": max(self._policy.fused_k, 40),
                "rerank_k": max(self._policy.rerank_k, 10),
                "max_chunks_per_document": max(self._policy.max_chunks_per_document, 3),
            }
        return {
            "bm25_k": self._policy.bm25_k,
            "vector_k": self._policy.vector_k,
            "fused_k": self._policy.fused_k,
            "rerank_k": self._policy.rerank_k,
            "max_chunks_per_document": self._policy.max_chunks_per_document,
        }
