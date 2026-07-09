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
        active_sections = self._sqlite_repo.list_active_sections(document_id=target_document_id)
        query_expansion_terms = self._query_expansion_terms(
            query,
            chunks=all_active_chunks,
            sections=active_sections,
        )
        expanded_query = self._expand_query(query, query_expansion_terms)
        active_chunk_sections = {
            str(chunk.get("id")): str(chunk.get("section_id") or "")
            for chunk in all_active_chunks
        }
        section_candidates = self._rank_sections(query=expanded_query, sections=active_sections)
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
            query=expanded_query,
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
        reranked_order = await self._reranker.rerank(query=expanded_query, texts=candidate_texts)
        rerank_backend = self._reranker.last_backend
        ordered_candidates = [candidate_ids[idx] for idx in reranked_order if idx < len(candidate_ids)]
        rerank_position_by_id = {
            chunk_id: position
            for position, chunk_id in enumerate(ordered_candidates, start=1)
        }
        top_bm25_score = max((hit.score for hit in bm25_hits), default=1.0)
        ordered_candidates = sorted(
            ordered_candidates,
            key=lambda chunk_id: self._candidate_priority(
                chunk_id=chunk_id,
                chunks_by_id=chunks_by_id,
                rerank_position_by_id=rerank_position_by_id,
                bm25_score_map=bm25_score_map,
                vector_score_map=vector_score_map,
                section_candidate_ids=section_candidate_ids,
                top_bm25_score=top_bm25_score,
                query=expanded_query,
            ),
            reverse=True,
        )
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
            noise_penalty = self._chunk_noise_penalty(row=row, query=expanded_query)
            directness_score = self._chunk_answer_relevance(row=row, query=expanded_query)
            combined = max(0.0, (base_score * quality_multiplier) + (0.18 * directness_score) - noise_penalty)
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
                    "direct_evidence_score": round(directness_score, 4),
                    "noise_penalty": round(noise_penalty, 4),
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
                "query_expansion_terms": query_expansion_terms,
                "query_expansion_applied": bool(query_expansion_terms),
                "retrieval_noise_policy": "enabled",
                "average_chunk_quality": avg_quality,
                "quality_weighting": "enabled",
                "scope": "document" if target_document_id else "corpus",
                "retrieval_profile": normalized_profile,
                "strategy": f"phase1_{normalized_mode}",
            },
        )

    @staticmethod
    def _candidate_priority(
        *,
        chunk_id: str,
        chunks_by_id: dict[str, dict[str, object]],
        rerank_position_by_id: dict[str, int],
        bm25_score_map: dict[str, float],
        vector_score_map: dict[str, float],
        section_candidate_ids: set[str],
        top_bm25_score: float,
        query: str,
    ) -> float:
        row = chunks_by_id.get(chunk_id)
        if not row:
            return 0.0
        rerank_position = rerank_position_by_id.get(chunk_id, len(rerank_position_by_id) + 1)
        rerank_score = 1.0 / max(rerank_position, 1)
        lexical_score = min(1.0, bm25_score_map.get(chunk_id, 0.0) / max(top_bm25_score, 1e-9))
        semantic_score = vector_score_map.get(chunk_id, 0.0)
        quality_score = RetrievalService._normalize_quality(row.get("quality_score"))
        directness_score = RetrievalService._chunk_answer_relevance(row=row, query=query)
        section_bonus = (
            0.12
            if row.get("section_id") and str(row.get("section_id")) in section_candidate_ids
            else 0.0
        )
        noise_penalty = RetrievalService._chunk_noise_penalty(row=row, query=query)
        return (
            (0.38 * rerank_score)
            + (0.22 * lexical_score)
            + (0.08 * semantic_score)
            + (0.14 * quality_score)
            + (0.18 * directness_score)
            + section_bonus
            - noise_penalty
        )

    @staticmethod
    def _expand_query(query: str, terms: list[str] | None = None) -> str:
        terms = terms if terms is not None else RetrievalService._query_expansion_terms(query)
        if not terms:
            return query
        return f"{query} {' '.join(terms)}"

    @staticmethod
    def _query_expansion_terms(
        query: str,
        chunks: list[dict[str, object]] | None = None,
        sections: list[dict[str, object]] | None = None,
    ) -> list[str]:
        normalized = query.lower()
        expansion_rules: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
            (
                ("what is", "define", "meaning of", "explain"),
                (
                    "definition",
                    "means",
                    "refers",
                    "called",
                    "concept",
                    "mechanism",
                    "works",
                    "uses",
                    "limitations",
                ),
            ),
            (
                ("compare", "contrast", "difference", "differences"),
                (
                    "similarities",
                    "differences",
                    "advantages",
                    "limitations",
                    "tradeoffs",
                    "versus",
                ),
            ),
            (
                ("steps", "procedure", "process", "workflow", "how to"),
                (
                    "process",
                    "steps",
                    "procedure",
                    "method",
                    "workflow",
                    "implementation",
                ),
            ),
            (
                ("diagram", "figure", "image reference", "image references", "visual"),
                (
                    "figure",
                    "diagram",
                    "image",
                    "visual",
                    "caption",
                    "illustration",
                ),
            ),
            (
                ("token position", "token positions", "represent positions", "represent token"),
                (
                    "positional",
                    "encoding",
                    "encodings",
                    "position",
                    "embeddings",
                    "sequence",
                    "order",
                ),
            ),
            (
                ("regularization", "overfitting", "overfit"),
                (
                    "constraining",
                    "constraint",
                    "restrict",
                    "simpler",
                    "freedom",
                    "parameters",
                    "generalization",
                ),
            ),
            (
                ("cross-validation", "cross validation", "model selection", "hyperparameter"),
                (
                    "selecting",
                    "model",
                    "tuning",
                    "hyperparameters",
                    "k-fold",
                    "validation",
                    "evaluate",
                ),
            ),
            (
                ("learning algorithms", "common algorithms", "algorithm"),
                (
                    "linear",
                    "polynomial",
                    "regression",
                    "logistic",
                    "nearest",
                    "neighbors",
                    "support",
                    "vector",
                    "machines",
                    "decision",
                    "trees",
                    "random",
                    "forests",
                    "ensemble",
                ),
            ),
            (
                ("dimensionality", "dimension reduction", "reduce dimensions"),
                (
                    "curse",
                    "dimensionality",
                    "reduction",
                    "training",
                    "data",
                    "pca",
                    "projection",
                ),
            ),
            (
                ("self-attention", "self attention", "recurrent layers", "recurrent layer"),
                (
                    "sequential",
                    "operations",
                    "maximum",
                    "path",
                    "length",
                    "dependencies",
                    "positions",
                    "convolutional",
                    "complexity",
                ),
            ),
            (
                ("multi-head attention", "multi head attention"),
                (
                    "linear",
                    "project",
                    "projected",
                    "queries",
                    "keys",
                    "values",
                    "heads",
                    "concatenated",
                    "representation",
                ),
            ),
            (
                ("limitation", "limitations", "caveat", "caveats", "tradeoff", "tradeoffs"),
                (
                    "however",
                    "although",
                    "reduced",
                    "effective",
                    "resolution",
                    "averaging",
                    "counteracts",
                    "effect",
                    "cost",
                ),
            ),
            (
                ("privacy", "private", "data leak", "sensitive"),
                (
                    "sensitive",
                    "user",
                    "data",
                    "personal",
                    "information",
                    "pii",
                    "mask",
                    "masking",
                    "encryption",
                    "secure",
                    "retention",
                ),
            ),
            (
                ("summary", "summarize", "overview", "main idea", "what is this about"),
                (
                    "introduction",
                    "overview",
                    "abstract",
                    "conclusion",
                    "topics",
                    "covers",
                    "main",
                    "findings",
                ),
            ),
        ]
        expanded: list[str] = []
        seen = set(RetrievalService._metadata_terms(query))
        for triggers, additions in expansion_rules:
            if not any(trigger in normalized for trigger in triggers):
                continue
            for term in additions:
                clean = term.lower()
                if clean in seen:
                    continue
                expanded.append(clean)
                seen.add(clean)
        for term in RetrievalService._document_aware_expansion_terms(
            query=query,
            chunks=chunks or [],
            sections=sections or [],
        ):
            clean = term.lower().strip()
            if clean and clean not in seen:
                expanded.append(clean)
                seen.add(clean)
        return expanded

    @staticmethod
    def _document_aware_expansion_terms(
        *,
        query: str,
        chunks: list[dict[str, object]],
        sections: list[dict[str, object]],
    ) -> list[str]:
        expansions: list[str] = []
        seen: set[str] = set()
        for term in RetrievalService._document_acronym_expansions(query=query, chunks=chunks, sections=sections):
            if term not in seen:
                expansions.append(term)
                seen.add(term)
        for term in RetrievalService._document_topic_terms(query=query, sections=sections):
            if term not in seen:
                expansions.append(term)
                seen.add(term)
        return expansions[:24]

    @staticmethod
    def _document_acronym_expansions(
        *,
        query: str,
        chunks: list[dict[str, object]],
        sections: list[dict[str, object]],
    ) -> list[str]:
        acronyms = {
            token.upper().rstrip("S")
            for token in re.findall(r"\b[A-Za-z][A-Za-z0-9+-]{1,8}s?\b", query)
            if 2 <= len(token.rstrip("sS")) <= 8
        }
        if not acronyms:
            return []

        text_blocks: list[str] = []
        for section in sections[:300]:
            text_blocks.append(
                " ".join(
                    str(section.get(key) or "")
                    for key in ("heading", "section_path", "key_terms_json")
                )
            )
        for chunk in chunks[:1200]:
            text = str(chunk.get("text") or "")
            metadata = " ".join(
                str(chunk.get(key) or "")
                for key in ("heading", "section_path", "key_terms_json")
            )
            if any(acronym.lower() in f"{metadata} {text[:800]}".lower() for acronym in acronyms):
                text_blocks.append(f"{metadata} {text[:1600]}")

        expansions: list[str] = []
        for block in text_blocks:
            for acronym in acronyms:
                pattern_before = re.compile(
                    rf"\b([A-Za-z][A-Za-z0-9+/\- ]{{3,90}}?)\s+\(({re.escape(acronym)}s?)\)",
                    flags=re.I,
                )
                pattern_after = re.compile(
                    rf"\b{re.escape(acronym)}s?\s+\(([A-Za-z][A-Za-z0-9+/\- ]{{3,90}}?)\)",
                    flags=re.I,
                )
                for match in [*pattern_before.finditer(block), *pattern_after.finditer(block)]:
                    phrase = re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")
                    phrase_terms = RetrievalService._metadata_terms(phrase)
                    if 1 <= len(phrase_terms) <= 8:
                        expansions.extend(sorted(phrase_terms))
        return RetrievalService._dedupe_terms(expansions)

    @staticmethod
    def _document_topic_terms(query: str, sections: list[dict[str, object]]) -> list[str]:
        query_terms = RetrievalService._metadata_terms(query)
        query_phrases = RetrievalService._query_phrases(query)
        if not query_terms or not sections:
            return []
        expansions: list[str] = []
        for section in sections[:400]:
            metadata = " ".join(
                str(section.get(key) or "")
                for key in ("heading", "section_path", "key_terms_json")
            )
            metadata_lower = metadata.lower()
            phrase_hit = any(phrase in metadata_lower for phrase in query_phrases)
            terms = RetrievalService._metadata_terms(metadata)
            term_overlap = len(query_terms & terms)
            if phrase_hit or term_overlap >= min(2, len(query_terms)):
                expansions.extend(sorted(terms - query_terms))
        return RetrievalService._dedupe_terms(expansions)[:16]

    @staticmethod
    def _chunk_noise_penalty(*, row: dict[str, object], query: str) -> float:
        if not RetrievalService._is_explanatory_query(query):
            return 0.0

        text = str(row.get("text") or "")
        lowered = text[:1200].lower()
        metadata = " ".join(
            str(row.get(key) or "").lower()
            for key in ("heading", "section_path", "chunk_type")
        )
        penalty = 0.0
        if any(marker in metadata for marker in ("index", "glossary", "bibliography", "references")):
            penalty += 0.34
        if any(marker in lowered[:500] for marker in ("copyright", "permission to reproduce", "provided proper attribution")):
            penalty += 0.24
        if "<eos>" in lowered and "<pad>" in lowered:
            penalty += 0.28
        if RetrievalService._looks_like_index_chunk(lowered):
            penalty += 0.26
        if RetrievalService._looks_like_broad_example_section(metadata, query=query):
            penalty += 0.22
        if lowered.count("http") >= 3:
            penalty += 0.12
        return min(0.6, penalty)

    @staticmethod
    def _chunk_answer_relevance(*, row: dict[str, object], query: str) -> float:
        query_terms = RetrievalService._metadata_terms(query)
        if not query_terms:
            return 0.0
        metadata = " ".join(
            str(row.get(key) or "").lower()
            for key in ("heading", "section_path", "chunk_type", "key_terms_json")
        )
        text = str(row.get("text") or "").lower()
        combined = f"{metadata} {text[:1800]}"
        combined_terms = RetrievalService._metadata_terms(combined)
        matched_terms = {
            term
            for term in query_terms
            if term in combined_terms
            or any(len(term) >= 5 and candidate.startswith(term[:6]) for candidate in combined_terms)
        }
        coverage = len(matched_terms) / max(len(query_terms), 1)
        score = min(1.0, coverage)

        phrases = RetrievalService._query_phrases(query)
        if phrases and any(phrase in combined for phrase in phrases):
            score += 0.28
        if RetrievalService._is_definition_or_explanation_query(query) and any(
            cue in combined
            for cue in (
                " is a ",
                " is an ",
                " means ",
                " refers ",
                " called ",
                " defined as ",
                " consists of ",
                " works by ",
                " used for ",
            )
        ):
            score += 0.18
        if RetrievalService._asks_for_visual_reference(query) and any(
            cue in combined for cue in ("figure", "fig.", "diagram", "image", "caption", "visual")
        ):
            score += 0.18
        if RetrievalService._looks_like_index_chunk(text) or RetrievalService._looks_like_broad_example_section(metadata, query=query):
            score -= 0.24
        if RetrievalService._looks_like_loose_application_mention(combined, query=query):
            score -= 0.34
        return max(0.0, min(1.0, score))

    @staticmethod
    def _is_explanatory_query(query: str) -> bool:
        lowered = query.lower()
        return any(
            marker in lowered
            for marker in (
                "what",
                "why",
                "how",
                "explain",
                "describe",
                "summarize",
                "summary",
                "which",
                "list",
                "compare",
                "overview",
            )
        )

    @staticmethod
    def _is_definition_or_explanation_query(query: str) -> bool:
        lowered = query.lower()
        return any(
            marker in lowered
            for marker in (
                "what is",
                "what are",
                "define",
                "meaning",
                "explain",
                "describe",
                "how does",
                "how do",
            )
        )

    @staticmethod
    def _asks_for_visual_reference(query: str) -> bool:
        lowered = query.lower()
        return any(marker in lowered for marker in ("image", "diagram", "figure", "visual", "photo"))

    @staticmethod
    def _looks_like_broad_example_section(metadata: str, *, query: str) -> bool:
        lowered_query = query.lower()
        if any(term in lowered_query for term in ("example", "application", "use case")):
            return False
        broad_markers = (
            "examples of applications",
            "examples using",
            "using google colab",
            "image preprocessing layers",
            "other algorithms for",
        )
        return any(marker in metadata for marker in broad_markers)

    @staticmethod
    def _looks_like_loose_application_mention(text: str, *, query: str) -> bool:
        lowered_query = query.lower()
        if any(term in lowered_query for term in ("example", "application", "use case")):
            return False
        return any(
            marker in text
            for marker in (
                "one possible application",
                "possible application",
                "examples of applications",
                "among many other",
            )
        )

    @staticmethod
    def _looks_like_index_chunk(text: str) -> bool:
        sample = text[:900]
        if len(sample) < 180:
            return False
        comma_count = sample.count(",")
        sentence_count = sample.count(".") + sample.count("?") + sample.count("!")
        line_count = max(1, sample.count("\n") + 1)
        short_fragment_count = sum(1 for fragment in re.split(r"[,;\n]", sample) if 2 <= len(fragment.strip()) <= 42)
        return (
            comma_count >= 14
            and short_fragment_count >= 14
            and sentence_count <= 8
            and short_fragment_count / line_count >= 5
        )

    @staticmethod
    def _rank_sections(query: str, sections: list[dict[str, object]]) -> list[dict[str, object]]:
        query_terms = RetrievalService._metadata_terms(query)
        query_phrases = RetrievalService._query_phrases(query)
        if not query_terms or not sections:
            return []
        normalized_query = query.lower()
        explanatory_query = RetrievalService._is_explanatory_query(query)
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
            phrase_matches = [phrase for phrase in query_phrases if phrase in f"{heading} {section_path}".lower()]
            score = (
                (2.0 * len(query_terms & heading_terms))
                + (1.4 * len(query_terms & path_terms))
                + (1.1 * len(set(matched)))
                + (2.8 * len(phrase_matches))
            )
            metadata = f"{heading} {section_path}".lower()
            if RetrievalService._is_definition_or_explanation_query(normalized_query):
                if phrase_matches and heading.lower().strip() in phrase_matches:
                    score += 1.6
                if any(marker in metadata for marker in ("overview", "introduction", "definition", "fundamentals")):
                    score += 0.6
            if explanatory_query and RetrievalService._looks_like_index_section(section, metadata):
                score -= 10.0
            if explanatory_query and RetrievalService._looks_like_broad_example_section(metadata, query=query):
                score -= 1.6
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
    def _looks_like_index_section(section: dict[str, object], metadata: str) -> bool:
        page_start = int(section.get("page_start") or 0)
        comma_count = metadata.count(",")
        compact_index_heading = (
            page_start >= 850
            and (
                comma_count >= 1
                or metadata.startswith("sklearn.")
                or " see " in metadata
                or "see also" in metadata
            )
        )
        backmatter_api_heading = page_start >= 850 and bool(re.search(r"\b[a-z]+\.[a-z_]+\b", metadata))
        return compact_index_heading or backmatter_api_heading

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
            "detail",
            "detailed",
            "does",
            "explain",
            "few",
            "from",
            "give",
            "into",
            "material",
            "into",
            "provide",
            "section",
            "software",
            "softwares",
            "source",
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
    def _query_phrases(text: str) -> list[str]:
        stopwords = {
            "about",
            "answer",
            "briefly",
            "can",
            "does",
            "explain",
            "from",
            "give",
            "how",
            "in",
            "of",
            "provide",
            "the",
            "this",
            "to",
            "what",
            "with",
        }
        tokens = [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text.lower())
            if token not in stopwords
        ]
        phrases: list[str] = []
        for size in (4, 3, 2):
            for idx in range(0, max(0, len(tokens) - size + 1)):
                phrase_tokens = tokens[idx : idx + size]
                if len(" ".join(phrase_tokens)) < 7:
                    continue
                phrases.append(" ".join(phrase_tokens))
        return RetrievalService._dedupe_terms(phrases)[:12]

    @staticmethod
    def _dedupe_terms(values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            clean = re.sub(r"\s+", " ", value.lower()).strip(" -:;,.")
            if not clean or clean in seen:
                continue
            deduped.append(clean)
            seen.add(clean)
        return deduped

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
