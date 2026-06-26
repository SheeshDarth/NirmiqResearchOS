import json
import re

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
        all_active_chunks = list(active_chunks)
        active_chunk_sections = {
            str(chunk.get("id")): str(chunk.get("section_id") or "")
            for chunk in all_active_chunks
        }
        active_sections = self._sqlite_repo.list_active_sections(document_id=target_document_id)
        section_candidates = self._rank_sections(query=query, sections=active_sections)
        section_candidate_ids = {
            str(candidate["section_id"])
            for candidate in section_candidates
            if candidate.get("score", 0) > 0
        }
        section_first_enabled = bool(target_document_id and active_sections)
        section_filtered_chunk_count = len(active_chunks)
        if section_first_enabled and section_candidate_ids:
            scoped_chunks = [
                chunk
                for chunk in active_chunks
                if str(chunk.get("section_id") or "") in section_candidate_ids
            ]
            if scoped_chunks:
                active_chunks = scoped_chunks
                section_filtered_chunk_count = len(scoped_chunks)
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
            if section_candidate_ids:
                vector_hits = [
                    hit
                    for hit in vector_hits
                    if active_chunk_sections.get(str(hit.get("id") or "")) in section_candidate_ids
                ]

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
        active_chunk_ids = {str(chunk["id"]) for chunk in all_active_chunks}
        orphan_vector_hit_count = len([chunk_id for chunk_id in vector_ranked_ids if chunk_id not in active_chunk_ids])
        candidate_ids = [chunk_id for chunk_id in candidate_ids if chunk_id in chunks_by_id]

        candidate_texts = [str(chunks_by_id[cid]["text"]) for cid in candidate_ids if cid in chunks_by_id]
        reranked_order = await self._reranker.rerank(query=query, texts=candidate_texts)
        rerank_backend = self._reranker.last_backend
        ordered_candidates = [candidate_ids[idx] for idx in reranked_order if idx < len(candidate_ids)]
        rerank_position_by_id = {
            chunk_id: position
            for position, chunk_id in enumerate(ordered_candidates, start=1)
        }
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
        chunk_selection_reasons: list[dict[str, object]] = []
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
                    section_id=row.get("section_id"),
                    heading=row.get("heading"),
                    section_path=row.get("section_path"),
                    chunk_type=str(row.get("chunk_type") or "body"),
                )
            )
            chunk_selection_reasons.append(
                {
                    "chunk_id": chunk_id,
                    "final_rank": len(chunk_selection_reasons) + 1,
                    "source": source,
                    "lexical_hit": chunk_id in bm25_score_map,
                    "vector_hit": chunk_id in vector_score_map,
                    "section_match": bool(
                        row.get("section_id")
                        and str(row.get("section_id")) in section_candidate_ids
                    ),
                    "quality_score": quality_score,
                    "rerank_position": rerank_position_by_id.get(chunk_id),
                    "final_score": round(combined, 4),
                    "heading": row.get("heading"),
                    "section_path": row.get("section_path"),
                    "chunk_type": row.get("chunk_type") or "body",
                }
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
                "section_first_enabled": section_first_enabled,
                "section_candidate_count": len(section_candidates),
                "section_filtered_chunk_count": section_filtered_chunk_count,
                "section_candidates": section_candidates[:5],
                "chunk_selection_reasons": chunk_selection_reasons,
                "retrieval_diagnostics": {
                    "active_chunks_considered": len(all_active_chunks),
                    "active_sections_considered": len(active_sections),
                    "section_filter_applied": bool(section_candidate_ids),
                    "candidate_ids_after_fusion": len(candidate_ids),
                    "returned_chunks": len(chunks),
                },
                "average_chunk_quality": avg_quality,
                "quality_weighting": "enabled",
                "scope": "document" if target_document_id else "corpus",
                "retrieval_profile": normalized_profile,
                "strategy": f"phase1_{normalized_mode}",
            },
        )

    @staticmethod
    def _rank_sections(query: str, sections: list[dict[str, object]]) -> list[dict[str, object]]:
        query_terms = RetrievalService._metadata_terms(query)
        if not query_terms or not sections:
            return []
        ranked: list[tuple[float, dict[str, object]]] = []
        for section in sections:
            heading = str(section.get("heading") or "")
            section_path = str(section.get("section_path") or "")
            key_terms = RetrievalService._decode_key_terms(section.get("key_terms_json"))
            heading_terms = RetrievalService._metadata_terms(heading)
            path_terms = RetrievalService._metadata_terms(section_path)
            metadata_terms = heading_terms | path_terms | set(key_terms)
            matched = sorted(
                term
                for term in query_terms
                if term in metadata_terms
                or any(len(term) >= 5 and candidate.startswith(term[:6]) for candidate in metadata_terms)
            )
            score = (
                (2.0 * len(query_terms & heading_terms))
                + (1.4 * len(query_terms & path_terms))
                + (1.1 * len(set(matched)))
            )
            if score <= 0:
                continue
            ranked.append(
                (
                    score,
                    {
                        "section_id": str(section.get("id")),
                        "heading": heading,
                        "section_path": section_path,
                        "page_start": section.get("page_start"),
                        "page_end": section.get("page_end"),
                        "score": round(score, 3),
                        "matched_terms": matched,
                    },
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in ranked[:5]]

    @staticmethod
    def _metadata_terms(text: str) -> set[str]:
        stopwords = {
            "about",
            "after",
            "also",
            "and",
            "answer",
            "are",
            "chapter",
            "does",
            "explain",
            "from",
            "give",
            "into",
            "section",
            "that",
            "the",
            "this",
            "what",
            "when",
            "where",
            "which",
            "with",
        }
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text.lower())
            if token not in stopwords and len(token) >= 4
        }

    @staticmethod
    def _decode_key_terms(raw_value: object) -> list[str]:
        if not raw_value:
            return []
        try:
            loaded = json.loads(str(raw_value))
        except json.JSONDecodeError:
            return []
        if not isinstance(loaded, list):
            return []
        return [str(item).lower() for item in loaded if str(item).strip()]

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
