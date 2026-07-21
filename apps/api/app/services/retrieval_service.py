import json
import math
import re
from dataclasses import dataclass

from app.adapters.llm.embedder import Embedder
from app.adapters.llm.reranker import Reranker
from app.adapters.retrieval.bm25_index import BM25Index
from app.adapters.retrieval.rrf_fuser import fuse_ranked_lists_with_scores
from app.adapters.storage.chroma_repo import ChromaRepo
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.core.config import Settings
from app.domain.answer_intelligence import (
    EvidenceObligation,
    answer_evidence_cue_score,
    answer_subject_anchor_terms,
    build_answer_plan,
    evidence_obligation_score,
)
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy


@dataclass(slots=True)
class _ActiveDocumentRows:
    manifest: tuple[str, str, str, str, int]
    chunks: list[dict[str, object]]
    sections: list[dict[str, object]]


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
        self._active_document_cache: dict[str, _ActiveDocumentRows] = {}
        self._active_document_cache_hits = 0
        self._active_document_cache_misses = 0

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
        response_mode: str = "research",
        answer_query: str | None = None,
    ) -> RetrievalBundle:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"hybrid", "bm25", "vector"}:
            normalized_mode = "hybrid"
        normalized_profile = profile.strip().lower()
        if normalized_profile not in {"fast", "balanced", "precision"}:
            normalized_profile = "balanced"
        target_document_id = document_id.strip() if document_id and document_id.strip() else None
        profile_config = self._profile_config(normalized_profile)
        requested_query = answer_query.strip() if answer_query and answer_query.strip() else query
        answer_plan = build_answer_plan(query=requested_query, response_mode=response_mode)

        document_rows_cache_hit = False
        if target_document_id:
            active_chunks, active_sections, document_rows_cache_hit = self._load_active_document_rows(
                target_document_id
            )
        else:
            active_chunks = self._sqlite_repo.list_active_chunks(document_id=None)
            active_sections = self._sqlite_repo.list_active_sections(document_id=None)
        all_active_chunks = list(active_chunks)
        document_acronym_expansion_terms = self._document_acronym_expansions(
            query=query,
            chunks=all_active_chunks,
            sections=active_sections,
        )
        if document_acronym_expansion_terms:
            document_query_expansion_terms = list(document_acronym_expansion_terms)
        else:
            document_query_expansion_terms = self._document_topic_terms(
                query=query,
                sections=active_sections,
            )
        query_expansion_terms = self._query_expansion_terms(query)
        for term in document_query_expansion_terms:
            if term not in query_expansion_terms:
                query_expansion_terms.append(term)
        subject_query = self._expand_query(query, document_query_expansion_terms)
        expanded_query = self._expand_query(query, query_expansion_terms)
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
                section_filtered_chunk_count = len(scoped_chunks)
        asks_for_exercise_content = bool(
            re.search(r"\b(?:exercise|exercises|practice\s+question|question\s+bank)\b", requested_query, re.I)
        )
        if self._is_explanatory_query(subject_query):
            readable_chunks = [
                chunk
                for chunk in active_chunks
                if not self._looks_like_index_chunk(str(chunk.get("text") or "").lower())
                and not self._looks_like_answer_key_chunk(chunk)
                and (
                    asks_for_exercise_content
                    or not self._looks_like_exercise_question_chunk(str(chunk.get("text") or ""))
                )
            ]
            if readable_chunks:
                active_chunks = readable_chunks
                section_filtered_chunk_count = len(readable_chunks)
        obligation_queries = (
            answer_plan.evidence_queries(requested_query)
            if target_document_id
            else {}
        )
        batched_queries = {"__base__": expanded_query}
        batched_queries.update(
            {
                f"obligation:{key}": self._expand_query(value, query_expansion_terms)
                for key, value in obligation_queries.items()
            }
        )
        bm25_batches = await self._bm25_index.search_many(
            queries=batched_queries,
            chunks=active_chunks,
            limit=profile_config["bm25_k"],
        )
        bm25_corpus_cache_hit = self._bm25_index.last_cache_hit
        bm25_corpus_cache_stats = self._bm25_index.stats()
        bm25_hits = bm25_batches.get("__base__", [])

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
        active_chunks_by_id = {
            str(row.get("id") or ""): row
            for row in active_chunks
            if row.get("id")
        }
        obligation_candidate_map: dict[str, list[str]] = {}
        obligation_score_map: dict[str, float] = {}
        obligation_keys_by_id: dict[str, list[str]] = {}
        core_subject_terms = answer_subject_anchor_terms(requested_query, answer_plan)
        for obligation in answer_plan.evidence_obligations[:4]:
            hits = bm25_batches.get(f"obligation:{obligation.key}", [])
            top_score = max((hit.score for hit in hits), default=1.0)
            scored_hits: list[tuple[float, str]] = []
            for hit in hits:
                row = active_chunks_by_id.get(hit.chunk_id)
                if not row:
                    continue
                text = str(row.get("text") or "")
                lowered = text.lower()
                if self._looks_like_index_chunk(lowered) or self._looks_like_answer_key_chunk(row):
                    continue
                normalized_score = min(1.0, hit.score / max(top_score, 1e-9))
                cue_score = evidence_obligation_score(obligation, text)
                directness = self._chunk_answer_relevance(
                    row=row,
                    query=expanded_query,
                    answer_query=requested_query,
                )
                if obligation.key.startswith("comparison_side_") and cue_score < 0.32:
                    continue
                core_hits = sum(1 for term in core_subject_terms if term in lowered)
                core_coverage = core_hits / max(len(core_subject_terms), 1)
                if normalized_score < 0.2 and cue_score < 0.42:
                    continue
                if directness < 0.22 and cue_score < 0.42:
                    continue
                if core_subject_terms and core_hits <= 0 and not (
                    directness >= 0.55 and cue_score >= 0.42
                ):
                    continue
                structural_score = self._structural_identifier_score(
                    query=requested_query,
                    text=text,
                )
                noise_penalty = self._chunk_noise_penalty(row=row, query=requested_query)
                combined_obligation_score = max(0.0, min(
                    1.0,
                    (0.32 * normalized_score)
                    + (0.28 * cue_score)
                    + (0.22 * directness)
                    + (0.12 * core_coverage)
                    + (0.18 * structural_score)
                    - noise_penalty,
                ))
                scored_hits.append((combined_obligation_score, hit.chunk_id))

            accepted = [
                chunk_id
                for _, chunk_id in sorted(scored_hits, reverse=True)[:2]
            ]
            for combined_obligation_score, chunk_id in sorted(scored_hits, reverse=True)[:2]:
                obligation_score_map[chunk_id] = max(
                    obligation_score_map.get(chunk_id, 0.0),
                    combined_obligation_score,
                )
                obligation_keys_by_id.setdefault(chunk_id, []).append(obligation.key)
            obligation_candidate_map[obligation.key] = accepted

        obligation_recovery_ids = list(
            dict.fromkeys(
                chunk_id
                for ids in obligation_candidate_map.values()
                for chunk_id in ids
            )
        )
        for chunk_id in obligation_recovery_ids:
            if chunk_id not in candidate_ids:
                candidate_ids.append(chunk_id)
        candidate_ids = candidate_ids[: profile_config["fused_k"] + 8]
        roadmap_rescue_ids = self._roadmap_rescue_candidate_ids(
            query=requested_query,
            chunks=all_active_chunks if target_document_id else active_chunks,
            existing_ids=set(candidate_ids),
            limit=3,
        ) if answer_plan.answer_type in {"enumeration", "workflow_placement"} else []
        if roadmap_rescue_ids:
            rescued = set(roadmap_rescue_ids)
            candidate_ids = [
                *roadmap_rescue_ids,
                *[chunk_id for chunk_id in candidate_ids if chunk_id not in rescued],
            ][: profile_config["fused_k"] + 8]
        anchor_rescue_ids = self._anchor_rescue_candidate_ids(
            query=expanded_query,
            answer_query=requested_query,
            chunks=all_active_chunks if target_document_id else active_chunks,
            existing_ids=set(candidate_ids),
            limit=min(3, profile_config["fused_k"]),
        )
        if anchor_rescue_ids:
            rescued = set(anchor_rescue_ids)
            candidate_ids = [*anchor_rescue_ids, *[chunk_id for chunk_id in candidate_ids if chunk_id not in rescued]]
            candidate_ids = candidate_ids[: profile_config["fused_k"] + 8]
        neighbor_rescue_ids: list[str] = []
        neighbor_obligation_priority_ids: list[str] = []
        neighbor_answer_types = {
            "concept_explanation",
            "comparison",
            "enumeration",
            "mechanism_explanation",
            "procedure",
            "workflow_placement",
        }
        if target_document_id and answer_plan.answer_type in neighbor_answer_types:
            neighbor_rescue_ids = self._page_neighbor_rescue_candidate_ids(
                anchor_ids=roadmap_rescue_ids or anchor_rescue_ids or candidate_ids[:3] or obligation_recovery_ids,
                chunks=all_active_chunks,
                existing_ids=set(candidate_ids),
                query=expanded_query,
                answer_query=requested_query,
                limit=10,
                page_radius=(
                    16
                    if answer_plan.answer_type == "concept_explanation"
                    else 2
                    if answer_plan.answer_type == "comparison"
                    else 3
                    if answer_plan.answer_type == "enumeration"
                    else 4
                ),
            )
            candidate_ids.extend(
                chunk_id
                for chunk_id in neighbor_rescue_ids
                if chunk_id not in candidate_ids
            )
            for obligation in answer_plan.evidence_obligations:
                ranked_neighbors = sorted(
                    (
                        (
                            evidence_obligation_score(
                                obligation,
                                str(active_chunks_by_id[chunk_id].get("text") or ""),
                            ),
                            chunk_id,
                        )
                        for chunk_id in neighbor_rescue_ids
                        if chunk_id in active_chunks_by_id
                    ),
                    reverse=True,
                )
                if ranked_neighbors and ranked_neighbors[0][0] >= 0.32:
                    neighbor_obligation_priority_ids.append(ranked_neighbors[0][1])
        if target_document_id and not asks_for_exercise_content:
            exercise_chunk_ids = {
                str(row.get("id") or "")
                for row in all_active_chunks
                if self._looks_like_exercise_question_chunk(str(row.get("text") or ""))
            }
            candidate_ids = [
                chunk_id for chunk_id in candidate_ids if chunk_id not in exercise_chunk_ids
            ]
        document_scope_fallback = False
        if target_document_id and not candidate_ids and active_chunks:
            candidate_ids = [str(chunk["id"]) for chunk in active_chunks[: profile_config["fused_k"]]]
            document_scope_fallback = True
        chunks_by_id = self._sqlite_repo.get_chunks_by_ids(candidate_ids)
        active_chunk_ids = {str(chunk["id"]) for chunk in all_active_chunks}
        orphan_vector_hit_count = len([chunk_id for chunk_id in vector_ranked_ids if chunk_id not in active_chunk_ids])
        candidate_ids = [chunk_id for chunk_id in candidate_ids if chunk_id in chunks_by_id]
        local_obligation_priority_ids: list[str] = []
        if answer_plan.answer_type not in {"document_summary", "enumeration", "workflow_placement"}:
            required_obligations = [
                obligation
                for obligation in answer_plan.evidence_obligations
                if obligation.required
            ]
            local_scores_by_chunk: dict[str, dict[str, float]] = {}
            for obligation in required_obligations:
                ranked_local_candidates = sorted(
                    (
                        (
                            self._local_obligation_evidence_score(
                                row=chunks_by_id[chunk_id],
                                obligation=obligation,
                                core_subject_terms=core_subject_terms,
                            ),
                            chunk_id,
                        )
                        for chunk_id in candidate_ids
                    ),
                    reverse=True,
                )
                for score, chunk_id in ranked_local_candidates:
                    local_scores_by_chunk.setdefault(chunk_id, {})[obligation.key] = score
                if ranked_local_candidates and ranked_local_candidates[0][0] >= 0.32:
                    local_obligation_priority_ids.append(ranked_local_candidates[0][1])
            if len(required_obligations) >= 2:
                joint_candidates: list[tuple[float, str]] = []
                for chunk_id, scores_by_key in local_scores_by_chunk.items():
                    scores = [
                        scores_by_key.get(obligation.key, 0.0)
                        for obligation in required_obligations
                    ]
                    if any(score < 0.32 for score in scores):
                        continue
                    joint_candidates.append(
                        (
                            min(scores) + (sum(scores) / len(scores)),
                            chunk_id,
                        )
                    )
                if joint_candidates:
                    local_obligation_priority_ids.insert(
                        0,
                        max(joint_candidates)[1],
                    )

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
                answer_query=requested_query,
                anchor_rescue_ids=set(anchor_rescue_ids),
                neighbor_rescue_ids=set(neighbor_rescue_ids),
                obligation_score_map=obligation_score_map,
                obligation_keys_by_id=obligation_keys_by_id,
                roadmap_rescue_ids=set(roadmap_rescue_ids),
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
        top_ids = self._preserve_lexical_guardrail(
            selected_ids=top_ids,
            bm25_ranked_ids=bm25_ranked_ids,
            chunks_by_id=chunks_by_id,
            query=requested_query,
            limit=profile_config["rerank_k"],
            protected_limit=min(5, profile_config["rerank_k"]),
        )
        required_obligation_ids = [
            obligation_candidate_map[obligation.key][0]
            for obligation in answer_plan.evidence_obligations
            if obligation.required and obligation_candidate_map.get(obligation.key)
        ]
        top_ids = self._preserve_priority_candidates(
            selected_ids=top_ids,
            priority_ids=[
                *local_obligation_priority_ids,
                *required_obligation_ids,
                *neighbor_obligation_priority_ids,
            ],
            limit=profile_config["rerank_k"],
        )

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
            noise_penalty = self._chunk_noise_penalty(row=row, query=requested_query)
            directness_score = self._chunk_answer_relevance(
                row=row,
                query=expanded_query,
                answer_query=requested_query,
            )
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
                    "evidence_obligations": obligation_keys_by_id.get(chunk_id, []),
                    "obligation_score": round(obligation_score_map.get(chunk_id, 0.0), 4),
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
                    "document_rows_cache_hit": document_rows_cache_hit,
                    "document_rows_cache_stats": self._active_document_cache_stats(),
                    "section_filter_applied": False,
                    "section_soft_ranking_applied": bool(section_candidate_ids),
                    "candidate_ids_after_fusion": len(candidate_ids),
                    "returned_chunks": len(chunks),
                    "obligation_candidate_count": len(obligation_recovery_ids),
                    "bm25_corpus_cache_hit": bm25_corpus_cache_hit,
                    "bm25_corpus_cache_stats": bm25_corpus_cache_stats,
                },
                "evidence_obligations": [
                    {
                        "key": item.key,
                        "label": item.label,
                        "required": item.required,
                    }
                    for item in answer_plan.evidence_obligations
                ],
                "obligation_candidates": obligation_candidate_map,
                "obligation_recovery_applied": bool(obligation_recovery_ids),
                "obligation_recovery_count": len(obligation_recovery_ids),
                "roadmap_rescue_applied": bool(roadmap_rescue_ids),
                "roadmap_rescue_count": len(roadmap_rescue_ids),
                "query_expansion_terms": query_expansion_terms,
                "query_expansion_applied": bool(query_expansion_terms),
                "document_query_expansion_terms": document_query_expansion_terms,
                "subject_expansion_applied": bool(document_query_expansion_terms),
                "document_acronym_expansion_terms": document_acronym_expansion_terms,
                "acronym_expansion_applied": bool(document_acronym_expansion_terms),
                "anchor_rescue_applied": bool(anchor_rescue_ids),
                "anchor_rescue_count": len(anchor_rescue_ids),
                "neighbor_rescue_applied": bool(neighbor_rescue_ids),
                "neighbor_rescue_count": len(neighbor_rescue_ids),
                "retrieval_noise_policy": "enabled",
                "average_chunk_quality": avg_quality,
                "quality_weighting": "enabled",
                "scope": "document" if target_document_id else "corpus",
                "retrieval_profile": normalized_profile,
                "retrieval_method": "nirmiq_evidence_first_hierarchical_hybrid_rag",
                "retrieval_method_version": "megasprint6.v1",
                "answer_plan_type": answer_plan.answer_type,
                "strategy": f"nirmiq_ehr_{normalized_mode}",
            },
        )

    def _load_active_document_rows(
        self, document_id: str
    ) -> tuple[list[dict[str, object]], list[dict[str, object]], bool]:
        document = self._sqlite_repo.get_document_by_id(document_id)
        if not document:
            self._active_document_cache.pop(document_id, None)
            self._active_document_cache_misses += 1
            return [], [], False

        active_chunk_count = self._sqlite_repo.get_active_chunk_count(document_id)
        manifest = (
            document_id,
            str(document.get("content_hash") or ""),
            str(document.get("status") or ""),
            str(document.get("updated_at") or ""),
            active_chunk_count,
        )
        cached = self._active_document_cache.get(document_id)
        if cached and cached.manifest == manifest:
            self._active_document_cache_hits += 1
            return cached.chunks, cached.sections, True

        chunks = self._sqlite_repo.list_active_chunks(document_id=document_id)
        sections = self._sqlite_repo.list_active_sections(document_id=document_id)
        self._active_document_cache[document_id] = _ActiveDocumentRows(
            manifest=manifest,
            chunks=chunks,
            sections=sections,
        )
        self._active_document_cache_misses += 1
        return chunks, sections, False

    def _active_document_cache_stats(self) -> dict[str, int]:
        return {
            "cached_documents": len(self._active_document_cache),
            "cache_hits": self._active_document_cache_hits,
            "cache_misses": self._active_document_cache_misses,
        }

    def runtime_cache_stats(self) -> dict[str, object]:
        return {
            "active_document_rows": self._active_document_cache_stats(),
            "bm25_corpus": self._bm25_index.stats(),
        }

    @staticmethod
    def _preserve_lexical_guardrail(
        *,
        selected_ids: list[str],
        bm25_ranked_ids: list[str],
        chunks_by_id: dict[str, dict[str, object]],
        query: str,
        limit: int,
        protected_limit: int,
    ) -> list[str]:
        """Keep clean top lexical evidence available after helper reranking."""

        if limit <= 0 or protected_limit <= 0:
            return selected_ids[: max(limit, 0)]
        protected: list[str] = []
        for chunk_id in bm25_ranked_ids:
            row = chunks_by_id.get(chunk_id)
            if not row:
                continue
            text = str(row.get("text") or "").lower()
            if (
                RetrievalService._looks_like_index_chunk(text)
                or RetrievalService._looks_like_answer_key_chunk(row)
                or RetrievalService._chunk_noise_penalty(row=row, query=query) >= 0.5
            ):
                continue
            protected.append(chunk_id)
            if len(protected) >= protected_limit:
                break

        result = list(dict.fromkeys(selected_ids[:limit]))
        protected_set = set(protected)
        for chunk_id in protected:
            if chunk_id in result:
                continue
            if len(result) < limit:
                result.append(chunk_id)
                continue
            replacement_index = next(
                (
                    index
                    for index in range(len(result) - 1, -1, -1)
                    if result[index] not in protected_set
                ),
                None,
            )
            if replacement_index is None:
                break
            result[replacement_index] = chunk_id
        return list(dict.fromkeys(result))[:limit]

    @staticmethod
    def _preserve_priority_candidates(
        *,
        selected_ids: list[str],
        priority_ids: list[str],
        limit: int,
    ) -> list[str]:
        """Keep one evidence candidate for every required answer obligation."""

        if limit <= 0:
            return []
        priorities = list(dict.fromkeys(priority_ids))[:limit]
        priority_set = set(priorities)
        result = list(dict.fromkeys(selected_ids))[:limit]
        for chunk_id in priorities:
            if chunk_id in result:
                continue
            if len(result) < limit:
                result.append(chunk_id)
                continue
            replacement_index = next(
                (
                    index
                    for index in range(len(result) - 1, -1, -1)
                    if result[index] not in priority_set
                ),
                None,
            )
            if replacement_index is None:
                break
            result[replacement_index] = chunk_id
        return list(dict.fromkeys(result))[:limit]

    @staticmethod
    def _local_obligation_evidence_score(
        *,
        row: dict[str, object],
        obligation: EvidenceObligation,
        core_subject_terms: set[str],
    ) -> float:
        """Score evidence only when the subject and operation share a local window."""

        text = re.sub(r"\s+", " ", str(row.get("text") or "")).strip()
        if not text:
            return 0.0
        sentences = [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip(" -")
        ]
        if not sentences:
            return 0.0
        roadmap_cues = (
            "covers the following topics",
            "in this section we will",
            "this chapter will",
            "learning objectives",
            "before we move on",
        )
        core_positions = [
            index
            for index, sentence in enumerate(sentences)
            if not any(cue in sentence.lower() for cue in roadmap_cues)
            and any(
                term in RetrievalService._metadata_terms(sentence)
                for term in core_subject_terms
            )
        ]
        if core_subject_terms and not core_positions:
            return 0.0

        best = 0.0
        for index, sentence in enumerate(sentences):
            obligation_score = evidence_obligation_score(obligation, sentence)
            if obligation_score < 0.32:
                continue
            if core_positions and min(abs(index - position) for position in core_positions) > 2:
                continue
            core_hits = len(
                core_subject_terms & RetrievalService._metadata_terms(sentence)
            )
            best = max(best, min(1.0, obligation_score + (0.05 * core_hits)))
        return best

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
        answer_query: str | None = None,
        anchor_rescue_ids: set[str] | None = None,
        neighbor_rescue_ids: set[str] | None = None,
        obligation_score_map: dict[str, float] | None = None,
        obligation_keys_by_id: dict[str, list[str]] | None = None,
        roadmap_rescue_ids: set[str] | None = None,
    ) -> float:
        row = chunks_by_id.get(chunk_id)
        if not row:
            return 0.0
        rerank_position = rerank_position_by_id.get(chunk_id, len(rerank_position_by_id) + 1)
        rerank_score = 1.0 / max(rerank_position, 1)
        lexical_score = min(1.0, bm25_score_map.get(chunk_id, 0.0) / max(top_bm25_score, 1e-9))
        semantic_score = vector_score_map.get(chunk_id, 0.0)
        quality_score = RetrievalService._normalize_quality(row.get("quality_score"))
        requested_query = answer_query or query
        directness_score = RetrievalService._chunk_answer_relevance(
            row=row,
            query=query,
            answer_query=requested_query,
        )
        section_bonus = (
            0.12
            if row.get("section_id") and str(row.get("section_id")) in section_candidate_ids
            else 0.0
        )
        noise_penalty = RetrievalService._chunk_noise_penalty(row=row, query=requested_query)
        anchor_bonus = (
            RetrievalService._anchor_rescue_priority_bonus(
                row=row,
                query=query,
                answer_query=requested_query,
            )
            if anchor_rescue_ids and chunk_id in anchor_rescue_ids
            else 0.0
        )
        neighbor_bonus = 0.0
        if neighbor_rescue_ids and chunk_id in neighbor_rescue_ids:
            neighbor_bonus = 0.48
            neighbor_text = str(row.get("text") or "").lower()
            if any(
                cue in neighbor_text
                for cue in ("building block", "composed of", "consists of", "goal is to", "works by")
            ):
                neighbor_bonus += 0.4
        obligation_score = (
            obligation_score_map.get(chunk_id, 0.0)
            if obligation_score_map
            else 0.0
        )
        obligation_diversity = min(
            3,
            len(obligation_keys_by_id.get(chunk_id, [])) if obligation_keys_by_id else 0,
        )
        structural_score = RetrievalService._structural_identifier_score(
            query=requested_query,
            text=str(row.get("text") or ""),
        )
        roadmap_bonus = 0.7 if roadmap_rescue_ids and chunk_id in roadmap_rescue_ids else 0.0
        return (
            (0.30 * rerank_score)
            + (0.22 * lexical_score)
            + (0.08 * semantic_score)
            + (0.12 * quality_score)
            + (0.28 * directness_score)
            + section_bonus
            + anchor_bonus
            + neighbor_bonus
            + (0.24 * obligation_score)
            + (0.04 * obligation_diversity)
            + (0.42 * structural_score)
            + roadmap_bonus
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
                    "avoid",
                    "store",
                    "storing",
                    "sensitive",
                    "sensive",
                    "user",
                    "data",
                    "personal",
                    "information",
                    "informaon",
                    "pii",
                    "mask",
                    "masking",
                    "encryption",
                    "secure",
                    "retention",
                    "retenon",
                ),
            ),
            (
                ("fact-check", "fact check", "verification", "verify outputs"),
                (
                    "cross-check",
                    "trusted",
                    "sources",
                    "retrieval-based",
                    "fallback",
                    "uncertain",
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
        acronym_expansions = RetrievalService._document_acronym_expansions(
            query=query,
            chunks=chunks,
            sections=sections,
        )
        if acronym_expansions:
            # Exact acronym expansion is already a strong document-local subject
            # signal. Adding every key term from the first matching section causes
            # circular drift into broad application/index sections.
            return acronym_expansions[:24]

        expansions: list[str] = []
        seen: set[str] = set()
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
        # Older textbook indexes can place the first acronym definition well past
        # chunk 1,200. The chunks are already loaded for retrieval, so this scan
        # extends coverage without another database read or model dependency.
        for chunk in chunks[:5000]:
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
                for match in pattern_before.finditer(block):
                    phrase = re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")
                    expansions.extend(
                        RetrievalService._acronym_long_form_terms(
                            phrase=phrase,
                            acronym=acronym,
                            long_form_before=True,
                        )
                    )
                for match in pattern_after.finditer(block):
                    phrase = re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")
                    expansions.extend(
                        RetrievalService._acronym_long_form_terms(
                            phrase=phrase,
                            acronym=acronym,
                            long_form_before=False,
                        )
                    )
        return RetrievalService._dedupe_terms(expansions)

    @staticmethod
    def _acronym_long_form_terms(
        *,
        phrase: str,
        acronym: str,
        long_form_before: bool,
    ) -> list[str]:
        """Extract a long form only when its initials exactly match the acronym."""
        acronym_key = re.sub(r"[^A-Z0-9]", "", acronym.upper())
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9+/-]*", phrase)
        if not acronym_key or not tokens:
            return []
        candidate_ranges = (
            ((start, len(tokens)) for start in range(len(tokens)))
            if long_form_before
            else ((0, end) for end in range(1, len(tokens) + 1))
        )
        candidates: list[list[str]] = []
        for start, end in candidate_ranges:
            candidate = tokens[start:end]
            initials = "".join(token[0].upper() for token in candidate if token)
            if initials == acronym_key:
                candidates.append(candidate)
        if not candidates:
            return []
        best = min(candidates, key=len)
        return [
            token.lower()
            for token in best
            if token.lower() not in {"a", "an", "and", "of", "the"}
        ]

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
        if RetrievalService._looks_like_answer_key_chunk(row):
            penalty += 0.5
        if RetrievalService._looks_like_exercise_question_chunk(lowered):
            penalty += 0.32
        if RetrievalService._looks_like_broad_example_section(metadata, query=query):
            penalty += 0.22
        if lowered.count("http") >= 3:
            penalty += 0.12
        return min(0.6, penalty)

    @staticmethod
    def _chunk_answer_relevance(
        *,
        row: dict[str, object],
        query: str,
        answer_query: str | None = None,
    ) -> float:
        requested_query = answer_query or query
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
        answer_plan = build_answer_plan(query=requested_query, response_mode="research")
        subject_terms = RetrievalService._metadata_terms(answer_plan.subject)
        core_subject_terms = answer_subject_anchor_terms(requested_query, answer_plan)
        matched_subject_terms = {
            term
            for term in subject_terms
            if term in combined_terms
            or any(len(term) >= 5 and candidate.startswith(term[:6]) for candidate in combined_terms)
        }
        subject_coverage = len(matched_subject_terms) / max(len(subject_terms), 1)
        core_subject_hits = sum(1 for term in core_subject_terms if term in combined_terms)
        core_subject_coverage = core_subject_hits / max(len(core_subject_terms), 1)
        plan_cue_score = answer_evidence_cue_score(answer_plan.answer_type, combined)

        phrases = RetrievalService._specific_query_phrases(requested_query)
        if phrases and any(phrase in combined for phrase in phrases):
            score += 0.28
        score += RetrievalService._subject_definition_score(query=requested_query, text=combined)
        if RetrievalService._is_definition_or_explanation_query(requested_query) and any(
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
        if RetrievalService._asks_for_visual_reference(requested_query) and any(
            cue in combined for cue in ("figure", "fig.", "diagram", "image", "caption", "visual")
        ):
            score += 0.18
        if plan_cue_score > 0 and core_subject_hits > 0 and (
            subject_coverage >= 0.5
            or core_subject_coverage >= 0.7
            or any(phrase in combined for phrase in phrases)
        ):
            score += 0.24 * plan_cue_score
        if (
            answer_plan.answer_type in {
                "mechanism_explanation",
                "procedure",
                "workflow_placement",
                "recommendation",
                "limitations",
            }
            and core_subject_terms
            and core_subject_hits <= 0
        ):
            score = min(score, 0.48)
        if RetrievalService._looks_like_index_chunk(text) or RetrievalService._looks_like_broad_example_section(
            metadata,
            query=requested_query,
        ):
            score -= 0.24
        if RetrievalService._looks_like_loose_application_mention(combined, query=requested_query):
            score -= 0.34
        return max(0.0, min(1.0, score))

    @staticmethod
    def _anchor_rescue_candidate_ids(
        *,
        query: str,
        answer_query: str | None = None,
        chunks: list[dict[str, object]],
        existing_ids: set[str],
        limit: int,
    ) -> list[str]:
        """Promote highly direct evidence that lexical/vector fusion can bury.

        This is intentionally lightweight and local. It helps legacy documents
        that do not yet have section metadata, OCR-noisy notes, and textbook
        definitions where one direct paragraph is better than many loose hits.
        """
        if not chunks or limit <= 0:
            return []

        requested_query = answer_query or query
        normalized_query = requested_query.lower()
        answer_plan = build_answer_plan(query=requested_query, response_mode="research")
        query_terms = RetrievalService._metadata_terms(query)
        subject_terms = RetrievalService._metadata_terms(answer_plan.subject)
        core_subject_terms = answer_subject_anchor_terms(requested_query, answer_plan)
        query_phrases = RetrievalService._specific_query_phrases(requested_query)
        scored: list[tuple[float, int, str]] = []
        for row in chunks:
            chunk_id = str(row.get("id") or "")
            if not chunk_id:
                continue
            text = str(row.get("text") or "")
            if not text.strip():
                continue
            text_lower = text.lower()
            if (
                RetrievalService._looks_like_index_chunk(text_lower)
                and not RetrievalService._asks_for_date_fact(requested_query)
            ):
                continue
            directness = RetrievalService._chunk_answer_relevance(
                row=row,
                query=query,
                answer_query=requested_query,
            )
            phrase_hits = sum(1 for phrase in query_phrases if phrase in text_lower)
            term_hits = sum(1 for term in query_terms if term in text_lower)
            subject_hits = sum(1 for term in subject_terms if term in text_lower)
            subject_coverage = subject_hits / max(len(subject_terms), 1)
            core_subject_hits = sum(1 for term in core_subject_terms if term in text_lower)
            core_subject_coverage = core_subject_hits / max(len(core_subject_terms), 1)
            plan_cue_score = answer_evidence_cue_score(answer_plan.answer_type, text_lower)
            cue_bonus = 0.0
            definition_anchor_score = RetrievalService._subject_definition_score(
                query=requested_query,
                text=text_lower,
            )
            acronym_definition_anchor = RetrievalService._contains_acronym_definition(
                query=requested_query,
                text=text,
            )
            if RetrievalService._is_definition_or_explanation_query(requested_query):
                if definition_anchor_score > 0:
                    cue_bonus += 0.9
                elif any(
                    cue in text_lower
                    for cue in (
                        " means ",
                        " refers ",
                        " assumes ",
                        " generated from ",
                        " generated by ",
                        " consists of ",
                    )
                ):
                    cue_bonus += 0.25
                if acronym_definition_anchor:
                    cue_bonus += 0.85
            if RetrievalService._asks_for_date_fact(requested_query) and (
                re.search(r"\b20\d{2}[-/]\d{2}[-/]\d{2}\b", text_lower)
                or "edition" in text_lower
                or "release" in text_lower
            ):
                cue_bonus += 0.9
            if "privacy" in normalized_query and any(
                cue in text_lower
                for cue in ("mask", "personal", "pii", "retention", "reten", "encrypt", "sensi")
            ):
                cue_bonus += 0.9
            if "dimensionality" in normalized_query and "curse of dimensionality" in text_lower:
                cue_bonus += 1.0

            score = (
                directness
                + (0.28 * phrase_hits)
                + (0.05 * term_hits)
                + cue_bonus
                + (
                    0.75 * plan_cue_score
                    if core_subject_hits > 0
                    and (subject_coverage >= 0.5 or core_subject_coverage >= 0.7 or phrase_hits > 0)
                    else 0.0
                )
                - RetrievalService._chunk_noise_penalty(row=row, query=requested_query)
            )
            if chunk_id in existing_ids:
                score += 0.05

            strong_definition_anchor = (
                answer_plan.answer_type == "concept_explanation"
                and directness >= 0.9
                and phrase_hits > 0
                and RetrievalService._is_definition_or_explanation_query(requested_query)
                and definition_anchor_score > 0
            )
            strong_acronym_anchor = (
                answer_plan.answer_type == "concept_explanation"
                and acronym_definition_anchor
                and directness >= 0.55
                and not RetrievalService._looks_like_index_chunk(text_lower)
            )
            strong_date_anchor = (
                RetrievalService._asks_for_date_fact(requested_query)
                and cue_bonus >= 0.9
                and directness >= 0.45
            )
            strong_privacy_anchor = (
                "privacy" in normalized_query
                and cue_bonus >= 0.9
                and directness >= 0.55
            )
            strong_dimensionality_anchor = (
                "dimensionality" in normalized_query
                and cue_bonus >= 1.0
                and directness >= 0.5
            )
            strong_plan_anchor = (
                answer_plan.answer_type in {
                    "mechanism_explanation",
                    "procedure",
                    "workflow_placement",
                    "recommendation",
                    "comparison",
                    "limitations",
                }
                and plan_cue_score >= 0.38
                and directness >= 0.55
                and core_subject_hits > 0
                and (subject_coverage >= 0.5 or core_subject_coverage >= 0.7 or phrase_hits > 0)
            )
            if score >= 1.1 and (
                strong_definition_anchor
                or strong_acronym_anchor
                or strong_date_anchor
                or strong_privacy_anchor
                or strong_dimensionality_anchor
                or strong_plan_anchor
            ):
                try:
                    page_start = int(row.get("page_start") or 1_000_000)
                except (TypeError, ValueError):
                    page_start = 1_000_000
                scored.append((score, page_start, chunk_id))

        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        rescued: list[str] = []
        seen: set[str] = set()
        for _, _, chunk_id in scored:
            if chunk_id in seen:
                continue
            rescued.append(chunk_id)
            seen.add(chunk_id)
            if len(rescued) >= limit:
                break
        return rescued

    @staticmethod
    def _roadmap_rescue_candidate_ids(
        *,
        query: str,
        chunks: list[dict[str, object]],
        existing_ids: set[str],
        limit: int,
    ) -> list[str]:
        """Recover document outlines and adjacent list-bearing roadmap chunks."""

        if not chunks or limit <= 0:
            return []
        normalized_query = query.lower()
        if not re.search(
            r"\b(?:cover|covers|covered|list|listed|overview|outline|topics?|workflow)\b",
            normalized_query,
        ):
            return []
        query_terms = RetrievalService._metadata_terms(query)
        scored: list[tuple[float, int, str]] = []
        for row in chunks:
            chunk_id = str(row.get("id") or "")
            text = str(row.get("text") or "")
            if not chunk_id or not text.strip():
                continue
            lowered = text.lower()
            roadmap_cues = sum(
                cue in lowered
                for cue in (
                    "covers the following topics",
                    "covers the following",
                    "the most common",
                    "steps in a typical",
                    "overview",
                    "learning objectives",
                )
            )
            list_density = min(1.0, (text.count(",") + text.count(";")) / 7.0)
            if roadmap_cues <= 0 and list_density < 0.55:
                continue
            text_terms = RetrievalService._metadata_terms(text)
            overlap = len(query_terms & text_terms) / max(len(query_terms), 1)
            structural_score = RetrievalService._structural_identifier_score(
                query=query,
                text=text,
            )
            if structural_score < 0:
                continue
            directness = RetrievalService._chunk_answer_relevance(
                row=row,
                query=query,
                answer_query=query,
            )
            try:
                page = int(row.get("page_start") or 1_000_000)
            except (TypeError, ValueError):
                page = 1_000_000
            early_bonus = 0.25 if "early" in normalized_query and page <= 80 else 0.0
            score = (
                (2.2 * overlap)
                + (1.4 * roadmap_cues)
                + (0.8 * list_density)
                + (2.5 * structural_score)
                + directness
                + early_bonus
                - RetrievalService._chunk_noise_penalty(row=row, query=query)
            )
            if chunk_id in existing_ids:
                score += 0.05
            if score >= 1.0:
                scored.append((score, -page, chunk_id))

        scored.sort(reverse=True)
        return [chunk_id for _, _, chunk_id in scored[:limit]]

    @staticmethod
    def _page_neighbor_rescue_candidate_ids(
        *,
        anchor_ids: list[str],
        chunks: list[dict[str, object]],
        existing_ids: set[str],
        query: str,
        answer_query: str,
        limit: int,
        page_radius: int = 14,
    ) -> list[str]:
        """Recover nearby subsections when legacy PDFs lack reliable heading metadata."""

        if not anchor_ids or limit <= 0:
            return []
        rows_by_id = {str(row.get("id") or ""): row for row in chunks}
        anchor_pages = [
            int(rows_by_id[chunk_id]["page_start"])
            for chunk_id in anchor_ids[:3]
            if chunk_id in rows_by_id and rows_by_id[chunk_id].get("page_start") is not None
        ]
        if not anchor_pages:
            return []
        anchor_pages = list(dict.fromkeys(anchor_pages))

        query_terms = RetrievalService._metadata_terms(query)
        query_acronyms = RetrievalService._query_acronyms(answer_query)
        scored: list[tuple[float, str]] = []
        for row in chunks:
            chunk_id = str(row.get("id") or "")
            page_value = row.get("page_start")
            if not chunk_id or chunk_id in existing_ids or page_value is None:
                continue
            page = int(page_value)
            distance = min(abs(page - anchor_page) for anchor_page in anchor_pages)
            if distance <= 0 or distance > page_radius:
                continue
            text = str(row.get("text") or "")
            lowered = text.lower()
            if (
                RetrievalService._looks_like_index_chunk(lowered)
                or RetrievalService._looks_like_answer_key_chunk(row)
                or (
                    not re.search(
                        r"\b(?:exercise|exercises|practice\s+question|question\s+bank)\b",
                        answer_query,
                        re.I,
                    )
                    and RetrievalService._looks_like_exercise_question_chunk(text)
                )
                or len(re.sub(r"\s+", " ", text).split()) < 18
            ):
                continue
            directness = RetrievalService._chunk_answer_relevance(
                row=row,
                query=query,
                answer_query=answer_query,
            )
            text_terms = RetrievalService._metadata_terms(text)
            term_hits = len(query_terms & text_terms)
            acronym_match = any(
                re.search(rf"\b{re.escape(acronym)}s?\b", text, flags=re.I)
                for acronym in query_acronyms
            )
            local_relevance = directness + min(0.35, 0.1 * term_hits) + (0.35 if acronym_match else 0.0)
            concept_cue_bonus = 0.7 if any(
                cue in lowered
                for cue in (
                    "building block",
                    "composed of",
                    "consists of",
                    "goal is to",
                    "works by",
                    "used to",
                )
            ) else 0.0
            if local_relevance < 0.2:
                continue
            quality = RetrievalService._normalize_quality(row.get("quality_score"))
            proximity = 1.0 - (distance / (page_radius + 1))
            scored.append(
                (
                    local_relevance
                    + concept_cue_bonus
                    + (0.25 * proximity)
                    + (0.08 * quality),
                    chunk_id,
                )
            )
        return [chunk_id for _, chunk_id in sorted(scored, reverse=True)[:limit]]

    @staticmethod
    def _anchor_rescue_priority_bonus(
        *,
        row: dict[str, object],
        query: str,
        answer_query: str | None = None,
    ) -> float:
        requested_query = answer_query or query
        text = str(row.get("text") or "").lower()
        directness = RetrievalService._chunk_answer_relevance(
            row=row,
            query=query,
            answer_query=requested_query,
        )
        phrases = RetrievalService._specific_query_phrases(requested_query)
        phrase_hit = any(phrase in text for phrase in phrases)
        lowered_query = requested_query.lower()
        answer_plan = build_answer_plan(query=requested_query, response_mode="research")
        subject_terms = RetrievalService._metadata_terms(answer_plan.subject)
        core_subject_terms = answer_subject_anchor_terms(requested_query, answer_plan)
        subject_hits = sum(1 for term in subject_terms if term in text)
        subject_coverage = subject_hits / max(len(subject_terms), 1)
        core_subject_hits = sum(1 for term in core_subject_terms if term in text)
        core_subject_coverage = core_subject_hits / max(len(core_subject_terms), 1)
        plan_cue_score = answer_evidence_cue_score(answer_plan.answer_type, text)
        if (
            answer_plan.answer_type == "concept_explanation"
            and directness >= 0.9
            and phrase_hit
            and RetrievalService._subject_definition_score(query=requested_query, text=text) > 0
        ):
            return 0.28
        if (
            answer_plan.answer_type == "concept_explanation"
            and directness >= 0.55
            and RetrievalService._contains_acronym_definition(query=requested_query, text=text)
            and not RetrievalService._looks_like_index_chunk(text)
        ):
            return 0.28
        if RetrievalService._asks_for_date_fact(requested_query) and directness >= 0.45:
            if re.search(r"\b20\d{2}[-/]\d{2}[-/]\d{2}\b", text) and (
                "edition" in text or "release" in text
            ):
                return 0.26
        if "privacy" in lowered_query and directness >= 0.55:
            if any(cue in text for cue in ("avoid storing", "mask personal", "limit data", "retention", "retenon")):
                return 0.22
        if "dimensionality" in lowered_query and "curse of dimensionality" in text:
            return 0.24
        if (
            answer_plan.answer_type in {
                "mechanism_explanation",
                "procedure",
                "workflow_placement",
                "recommendation",
                "comparison",
                "limitations",
            }
            and plan_cue_score >= 0.38
            and directness >= 0.55
            and core_subject_hits > 0
            and (subject_coverage >= 0.5 or core_subject_coverage >= 0.7 or phrase_hit)
        ):
            return 0.24
        return 0.0

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
    def _asks_for_date_fact(query: str) -> bool:
        return bool(
            re.search(
                r"\b(when|year|date|edition|release|released|publication|published)\b",
                query.lower(),
            )
        )

    @staticmethod
    def _contains_acronym_definition(*, query: str, text: str) -> bool:
        for acronym in RetrievalService._query_acronyms(query):
            escaped = re.escape(acronym)
            if re.search(
                rf"\b[A-Za-z][A-Za-z0-9+/-]*(?:\s+[A-Za-z][A-Za-z0-9+/-]*){{1,7}}\s+\({escaped}s?\)",
                text,
                flags=re.I,
            ):
                return True
            if re.search(rf"\b{escaped}s?\s+(?:is|are|means|refers|stands\s+for)\b", text, flags=re.I):
                return True
        return False

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
    def _subject_definition_score(*, query: str, text: str) -> float:
        phrases = RetrievalService._specific_query_phrases(query)
        if not phrases:
            return 0.0
        lowered = text.lower()
        score = 0.0
        for phrase in phrases:
            index = lowered.find(phrase)
            if index < 0:
                continue
            window = lowered[max(0, index - 80) : index + len(phrase) + 180]
            escaped = re.escape(phrase)
            definition_patterns = (
                rf"\b{escaped}\s*(\([^)]+\))?\s+is\s+(a|an|the)\b",
                rf"\b(a|an|the)\s+{escaped}\s*(\([^)]+\))?\s+is\s+(a|an|the)\b",
                rf"\b{escaped}\s+means\b",
                rf"\b{escaped}\s+refers\s+to\b",
                rf"\bcalled\s+{escaped}\b",
                rf"\bknown\s+as\s+{escaped}\b",
            )
            if any(re.search(pattern, window) for pattern in definition_patterns):
                score = max(score, 0.32)
            if "generated from" in window or "consists of" in window:
                score = max(score, 0.2)
        return score

    @staticmethod
    def _specific_query_phrases(query: str) -> list[str]:
        """Prefer an acronym's expanded long form over generic phrase suffixes."""
        tokens = [
            token
            for token in re.findall(r"[A-Za-z][A-Za-z0-9+-]{1,}", query)
            if token.lower()
            not in {
                "about",
                "answer",
                "define",
                "describe",
                "detail",
                "detailed",
                "explain",
                "from",
                "give",
                "provide",
                "source",
                "the",
                "this",
                "what",
                "with",
            }
        ]
        for index, token in enumerate(tokens):
            acronym = token.upper().rstrip("S")
            if not (2 <= len(acronym) <= 8 and (token.isupper() or len(acronym) <= 4)):
                continue
            for end in range(index + 2, min(len(tokens), index + len(acronym) + 3) + 1):
                candidate = tokens[index + 1 : end]
                initials = "".join(item[0].upper() for item in candidate)
                if initials == acronym:
                    return [" ".join(item.lower() for item in candidate)]
        return RetrievalService._query_phrases(query)

    @staticmethod
    def _looks_like_exercise_question_chunk(text: str) -> bool:
        sample = text[:1200].lower()
        question_marks = sample.count("?")
        numbered_questions = len(re.findall(r"\b\d{1,2}\.\s+(what|how|why|can|which|name|describe)\b", sample))
        practice_prompt = bool(
            re.search(r"\?\s*\d{1,2}\.\s+practice\b", sample)
            or re.search(r"\bexercises?\s+\d{1,2}\.\s+(?:practice|build|train|implement)\b", sample)
        )
        return question_marks >= 3 or numbered_questions >= 2 or practice_prompt

    @staticmethod
    def _looks_like_index_chunk(text: str) -> bool:
        sample = text[:900]
        comma_count = sample.count(",")
        sentence_count = sample.count(".") + sample.count("?") + sample.count("!")
        line_count = max(1, sample.count("\n") + 1)
        short_fragment_count = sum(1 for fragment in re.split(r"[,;\n]", sample) if 2 <= len(fragment.strip()) <= 42)
        dotted_identifier_count = len(
            re.findall(r"\b[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+(?:\(\))?", sample)
        )
        compact_cross_reference = (
            45 <= len(sample) < 180
            and sentence_count == 0
            and comma_count >= 1
            and sample.count("-") >= 1
        )
        dense_cross_reference = (
            sentence_count <= 2
            and comma_count >= 16
            and sample.count("-") >= 8
        )
        dense_api_index = (
            dotted_identifier_count >= 6
            and comma_count >= 10
            and short_fragment_count >= 10
        )
        return (
            compact_cross_reference
            or dense_cross_reference
            or dense_api_index
            or (
                comma_count >= 14
                and short_fragment_count >= 14
                and sentence_count <= 8
                and short_fragment_count / line_count >= 5
            )
        )

    @staticmethod
    def _looks_like_answer_key_chunk(row: dict[str, object]) -> bool:
        heading = str(row.get("heading") or "").strip().lower()
        return bool(
            re.match(r"^chapter\s+\d+\s*,\s+", heading)
            and len(re.findall(r"[a-zA-Z][a-zA-Z0-9+-]*", heading)) >= 8
        )

    @staticmethod
    def _rank_sections(query: str, sections: list[dict[str, object]]) -> list[dict[str, object]]:
        query_terms = RetrievalService._metadata_terms(query)
        query_phrases = RetrievalService._query_phrases(query)
        query_acronyms = RetrievalService._query_acronyms(query)
        if not query_terms or not sections:
            return []
        normalized_query = query.lower()
        explanatory_query = RetrievalService._is_explanatory_query(query)
        term_weights = RetrievalService._section_term_weights(query_terms=query_terms, sections=sections)
        ranked: list[tuple[float, dict[str, object]]] = []
        for section in sections:
            heading = str(section.get("heading") or "")
            section_path = str(section.get("section_path") or "")
            key_terms = RetrievalService._decode_key_terms(section.get("key_terms_json"))
            heading_terms = RetrievalService._metadata_terms(heading)
            path_terms = RetrievalService._metadata_terms(section_path)
            metadata_terms = heading_terms | path_terms | set(key_terms)
            metadata_acronyms = {
                token.lower().rstrip("s")
                for token in re.findall(r"\b[A-Z][A-Z0-9+-]{1,8}s?\b", f"{heading} {section_path}")
            }
            acronym_matches = query_acronyms & metadata_acronyms
            matched = sorted(
                term
                for term in query_terms
                if term in metadata_terms
                or any(len(term) >= 5 and candidate.startswith(term[:6]) for candidate in metadata_terms)
            )
            phrase_matches = [phrase for phrase in query_phrases if phrase in f"{heading} {section_path}".lower()]
            heading_weight = sum(term_weights.get(term, 1.0) for term in query_terms & heading_terms)
            path_weight = sum(term_weights.get(term, 1.0) for term in query_terms & path_terms)
            matched_weight = sum(term_weights.get(term, 1.0) for term in set(matched))
            score = (
                (2.0 * heading_weight)
                + (1.4 * path_weight)
                + (1.1 * matched_weight)
                + RetrievalService._section_phrase_score(
                    heading=heading,
                    section_path=section_path,
                    phrases=phrase_matches,
                    query_terms=query_terms,
                )
                + (35.0 * len(acronym_matches))
            )
            metadata = f"{heading} {section_path}".lower()
            if RetrievalService._is_definition_or_explanation_query(normalized_query):
                if phrase_matches and heading.lower().strip() in phrase_matches:
                    score += 1.6
                if any(marker in metadata for marker in ("overview", "introduction", "definition", "fundamentals")):
                    score += 0.6
            if explanatory_query and (
                RetrievalService._looks_like_index_section(section, metadata)
                or RetrievalService._looks_like_answer_key_chunk(section)
            ):
                continue
            if explanatory_query and RetrievalService._looks_like_broad_example_section(metadata, query=query):
                score -= 1.6
            score -= RetrievalService._section_modifier_penalty(
                heading=heading,
                phrase_matches=phrase_matches,
                query_terms=query_terms,
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
                        "matched_acronyms": sorted(acronym_matches),
                    },
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in ranked[:8]]

    @staticmethod
    def _query_acronyms(query: str) -> set[str]:
        acronyms = {
            token.lower().rstrip("s")
            for token in re.findall(r"\b[A-Z][A-Z0-9+-]{1,8}s?\b", query)
        }
        specific_phrases = RetrievalService._specific_query_phrases(query)
        if specific_phrases:
            initials = "".join(word[0] for word in specific_phrases[0].split() if word)
            for token in re.findall(r"\b[A-Za-z][A-Za-z0-9+-]{1,8}s?\b", query):
                normalized = token.lower().rstrip("s")
                if normalized == initials:
                    acronyms.add(normalized)
        return acronyms

    @staticmethod
    def _section_term_weights(*, query_terms: set[str], sections: list[dict[str, object]]) -> dict[str, float]:
        if not query_terms:
            return {}
        doc_freq = {term: 0 for term in query_terms}
        for section in sections:
            metadata_terms = RetrievalService._metadata_terms(
                " ".join(
                    str(section.get(key) or "")
                    for key in ("heading", "section_path", "key_terms_json")
                )
            )
            for term in query_terms:
                if term in metadata_terms:
                    doc_freq[term] += 1
        section_count = max(len(sections), 1)
        weights: dict[str, float] = {}
        for term in query_terms:
            frequency = doc_freq.get(term, 0)
            weights[term] = 1.0 + min(2.5, max(0.0, math.log((section_count + 1) / (frequency + 1))))
        return weights

    @staticmethod
    def _section_phrase_score(
        *,
        heading: str,
        section_path: str,
        phrases: list[str],
        query_terms: set[str],
    ) -> float:
        if not phrases:
            return 0.0
        heading_lower = heading.lower().strip()
        metadata = f"{heading} {section_path}".lower()
        score = 0.0
        for phrase in phrases:
            phrase_terms = set(phrase.split())
            if phrase_terms and not phrase_terms <= (query_terms | {"model", "models"}):
                continue
            if heading_lower.startswith(phrase):
                score += 4.0
            elif phrase in heading_lower:
                score += 2.0
            elif phrase in metadata:
                score += 1.2
        return score

    @staticmethod
    def _section_modifier_penalty(
        *,
        heading: str,
        phrase_matches: list[str],
        query_terms: set[str],
    ) -> float:
        if not phrase_matches:
            return 0.0
        heading_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", heading.lower())
        if not heading_tokens:
            return 0.0
        penalty = 0.0
        for phrase in phrase_matches:
            phrase_tokens = phrase.split()
            if not phrase_tokens:
                continue
            try:
                start = next(
                    index
                    for index in range(0, len(heading_tokens))
                    if heading_tokens[index : index + len(phrase_tokens)] == phrase_tokens
                )
            except StopIteration:
                continue
            leading_modifiers = [
                token
                for token in heading_tokens[:start]
                if token not in query_terms and token not in {"the", "and", "for", "with"}
            ]
            if leading_modifiers:
                penalty += min(3.0, 1.2 * len(leading_modifiers))
        return penalty

    @staticmethod
    def _looks_like_index_section(section: dict[str, object], metadata: str) -> bool:
        page_start = int(section.get("page_start") or 0)
        comma_count = metadata.count(",")
        compact_index_heading = (
            page_start >= 850
            and (
                comma_count >= 1
                or (metadata.count("-") >= 1 and len(metadata.split()) <= 18)
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
    def _structural_identifier_score(*, query: str, text: str) -> float:
        """Preserve requested Part/Chapter/Figure scope during retrieval."""

        pattern = re.compile(
            r"\b(part|chapter|section|figure|table)\s+([ivxlcdm]+|\d+(?:\.\d+)*)\b",
            flags=re.I,
        )
        requested = {(kind.lower(), value.lower()) for kind, value in pattern.findall(query)}
        if not requested:
            return 0.0
        present = {(kind.lower(), value.lower()) for kind, value in pattern.findall(text)}
        if requested & present:
            return 1.0
        requested_kinds = {kind for kind, _ in requested}
        if any(kind in requested_kinds for kind, _ in present):
            return -0.75
        return 0.0

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
