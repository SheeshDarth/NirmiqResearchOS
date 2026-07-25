import hashlib
import json
import re
from uuid import uuid4

from pydantic import ValidationError

from app.api.schemas.common import Citation
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.query import QueryRequest, QueryResponse
from app.domain.answer_intelligence import build_answer_plan
from app.domain.citation_coverage import citation_coverage
from app.domain.citations import to_citations
from app.domain.hierarchical_summary import select_hierarchical_summary_seeds
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.paper_lab import build_paper_lab_artifact
from app.domain.query_intent import QueryIntent, detect_query_intent
from app.domain.recursive_summary import (
    RECURSIVE_SUMMARY_VERSION,
    build_recursive_summary,
    render_recursive_summary,
)
from app.domain.summary_reliability import (
    audit_citation_support,
    validate_cached_summary,
    validate_persisted_summary_meta,
)
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.synthesis_service import SynthesisService


class QueryService:
    def __init__(
        self,
        memory_service: MemoryService,
        retrieval_service: RetrievalService,
        synthesis_service: SynthesisService,
        sqlite_repo: SQLiteRepo,
    ) -> None:
        self._memory_service = memory_service
        self._retrieval_service = retrieval_service
        self._synthesis_service = synthesis_service
        self._sqlite_repo = sqlite_repo

    async def run(self, payload: QueryRequest) -> QueryResponse:
        return await self._execute(payload=payload, persist=True)

    async def preview(self, payload: QueryRequest) -> QueryResponse:
        return await self._execute(payload=payload, persist=False)

    async def _execute(self, payload: QueryRequest, persist: bool) -> QueryResponse:
        _ = await self._memory_service.get_summary(payload.session_id)
        intent = detect_query_intent(payload.query, payload.mode)
        response_mode = self._resolve_response_mode(payload.mode, intent)
        retrieval_mode = self._resolve_retrieval_mode(
            mode=payload.mode,
            retrieval_mode=payload.retrieval_mode,
            document_id=payload.document_id,
            intent=intent,
        )
        retrieval_profile = self._resolve_retrieval_profile(payload.retrieval_profile, intent)
        cached_response = self._cached_summary_response(
            payload=payload,
            intent=intent,
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
        )
        if cached_response:
            if persist:
                self._persist_turn(
                    session_id=payload.session_id,
                    query=payload.query,
                    answer=cached_response.answer,
                    citations=cached_response.citations,
                    retrieval_meta=cached_response.retrieval_meta or {},
                )
                await self._memory_service.maybe_refresh_snapshot(payload.session_id)
            if not payload.debug:
                cached_response.retrieval_meta = None
            return cached_response

        recursive_summary_response = self._recursive_summary_response(
            payload=payload,
            intent=intent,
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
        )
        if recursive_summary_response:
            summary_meta = recursive_summary_response.retrieval_meta or {}
            self._store_summary_if_applicable(
                payload=payload,
                retrieval_mode=retrieval_mode,
                retrieval_profile=retrieval_profile,
                intent=intent,
                answer=recursive_summary_response.answer,
                citations=recursive_summary_response.citations,
                retrieval_meta=summary_meta,
            )
            if persist:
                self._persist_turn(
                    session_id=payload.session_id,
                    query=payload.query,
                    answer=recursive_summary_response.answer,
                    citations=recursive_summary_response.citations,
                    retrieval_meta=summary_meta,
                )
                await self._memory_service.maybe_refresh_snapshot(payload.session_id)
            if not payload.debug:
                recursive_summary_response.retrieval_meta = None
            return recursive_summary_response

        exam_context = self._build_exam_context(payload, intent)
        retrieval_query = self._retrieval_query(payload.query, response_mode, exam_context, intent)
        bundle = await self._retrieval_service.retrieve_with_mode(
            retrieval_query,
            mode=retrieval_mode,
            document_id=payload.document_id,
            profile=retrieval_profile,
            response_mode=response_mode,
            answer_query=payload.query,
        )
        bundle = self._augment_selected_summary_bundle(payload=payload, intent=intent, bundle=bundle)
        answer, grounded, synthesis_meta = await self._synthesis_service.synthesize(
            payload.query,
            bundle,
            response_mode=response_mode,
            exam_profile=payload.exam_profile.model_dump() if payload.exam_profile else None,
            exam_context=exam_context,
        )
        citations = self._citations_from_synthesis_context(bundle, synthesis_meta, grounded)
        combined_meta = {
            **bundle.meta,
            **synthesis_meta,
            "requested_retrieval_mode": payload.retrieval_mode,
            "effective_retrieval_mode": retrieval_mode,
            "retrieval_query_expanded": retrieval_query != payload.query,
            "requested_retrieval_profile": payload.retrieval_profile,
            "effective_retrieval_profile": retrieval_profile,
            "requested_response_mode": payload.mode,
            "response_mode": response_mode,
            "cache_hit": False,
            "detected_intent": intent.intent,
            "intent_confidence": intent.confidence,
            "intent_route": intent.route,
            "exam_profile": payload.exam_profile.model_dump() if payload.exam_profile else None,
            "exam_context": {
                "question_count": len(exam_context.get("questions", [])),
                "diagram_count": len(exam_context.get("diagrams", [])),
            },
        }
        if intent.intent == "summary":
            combined_meta["summary_profile"] = self._summary_profile(
                retrieval_mode=retrieval_mode,
                retrieval_profile=retrieval_profile,
                query=payload.query,
            )
            combined_meta["citation_support"] = audit_citation_support(
                answer,
                self._citation_source_rows(bundle, citations, synthesis_meta),
            )
        if intent.intent == "paper_draft":
            combined_meta["paper_lab"] = build_paper_lab_artifact(bundle.chunks)
        self._store_summary_if_applicable(
            payload=payload,
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
            intent=intent,
            answer=answer,
            citations=citations,
            retrieval_meta=combined_meta,
        )

        if persist:
            self._persist_turn(
                session_id=payload.session_id,
                query=payload.query,
                answer=answer,
                citations=citations,
                retrieval_meta=combined_meta,
            )
            await self._memory_service.maybe_refresh_snapshot(payload.session_id)

        return QueryResponse(
            session_id=payload.session_id,
            answer=answer,
            citations=citations,
            grounded=grounded,
            retrieval_meta=combined_meta if payload.debug else None,
        )

    def _cached_summary_response(
        self,
        *,
        payload: QueryRequest,
        intent: QueryIntent,
        retrieval_mode: str,
        retrieval_profile: str,
    ) -> QueryResponse | None:
        if not self._can_use_summary_cache(payload, intent):
            return None
        document = self._sqlite_repo.get_document_by_id(str(payload.document_id))
        if not document:
            return None
        summary_profile = self._summary_profile(
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
            query=payload.query,
        )
        cached = self._sqlite_repo.get_document_summary(
            document_id=str(payload.document_id),
            content_hash=str(document["content_hash"]),
            summary_profile=summary_profile,
        )
        if not cached:
            return None
        try:
            raw_citations = json.loads(str(cached["citations_json"]) or "[]")
            raw_retrieval_meta = json.loads(str(cached["retrieval_meta_json"]) or "{}")
            if not isinstance(raw_citations, list) or not isinstance(raw_retrieval_meta, dict):
                return None
            persisted_meta_validation = validate_persisted_summary_meta(raw_retrieval_meta)
            if not persisted_meta_validation["valid"]:
                return None
            citations = [Citation.model_validate(item) for item in raw_citations]
            retrieval_meta = raw_retrieval_meta
        except (json.JSONDecodeError, TypeError, ValueError, KeyError, ValidationError):
            return None
        retrieval_meta.update(
            {
                "cache_hit": True,
                "detected_intent": intent.intent,
                "intent_confidence": intent.confidence,
                "intent_route": "summary_cache_hit",
                "requested_retrieval_mode": payload.retrieval_mode,
                "effective_retrieval_mode": retrieval_mode,
                "requested_retrieval_profile": payload.retrieval_profile,
                "effective_retrieval_profile": retrieval_profile,
                "summary_profile": summary_profile,
            }
        )
        cache_validation = validate_cached_summary(
            str(cached["answer"]),
            [citation.model_dump() for citation in citations],
            retrieval_meta,
            active_rows=self._sqlite_repo.get_document_chunks(
                str(payload.document_id), active_only=True
            ),
            document_id=str(payload.document_id),
        )
        if not cache_validation["cache_consistent"]:
            return None
        retrieval_meta["citation_support"] = cache_validation["citation_support"]
        retrieval_meta["cache_validation"] = {
            "cache_consistent": cache_validation["cache_consistent"],
            "issues": cache_validation["issues"],
        }
        return QueryResponse(
            session_id=payload.session_id,
            answer=str(cached["answer"]),
            citations=citations,
            grounded=True,
            retrieval_meta=retrieval_meta,
        )

    def _recursive_summary_response(
        self,
        *,
        payload: QueryRequest,
        intent: QueryIntent,
        retrieval_mode: str,
        retrieval_profile: str,
    ) -> QueryResponse | None:
        if (
            not payload.document_id
            or intent.intent != "summary"
            or not self._is_document_wide_summary_query(payload.query)
        ):
            return None
        rows = self._sqlite_repo.get_document_chunks(str(payload.document_id), active_only=True)
        summary = build_recursive_summary(rows)
        if summary is None:
            return None
        answer, cited_rows = render_recursive_summary(summary)
        if not cited_rows:
            return None

        cited_chunks = [
            RetrievedChunk(
                chunk_id=str(row["id"]),
                document_id=str(row["document_id"]),
                text=str(row["text"]),
                score=float(row.get("quality_score") or 1.0),
                page_start=row.get("page_start"),
                page_end=row.get("page_end"),
                source="recursive_summary",
                quality_score=float(row.get("quality_score") or 1.0),
                section_id=row.get("section_id"),
                heading=row.get("heading"),
                section_path=row.get("section_path"),
                chunk_type=str(row.get("chunk_type") or "body"),
            )
            for row in cited_rows
        ]
        citations = to_citations(cited_chunks)
        cited_chunk_ids = [chunk.chunk_id for chunk in cited_chunks]
        coverage = citation_coverage(answer)
        citation_support = audit_citation_support(answer, cited_rows)
        summary_profile = self._summary_profile(
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
            query=payload.query,
        )
        retrieval_meta: dict[str, object] = {
            "strategy": "recursive_document_summary",
            "retrieval_method": "all_chunk_section_map_recursive_reduce",
            "requested_retrieval_mode": payload.retrieval_mode,
            "effective_retrieval_mode": retrieval_mode,
            "retrieval_query_expanded": False,
            "requested_retrieval_profile": payload.retrieval_profile,
            "effective_retrieval_profile": retrieval_profile,
            "requested_response_mode": payload.mode,
            "response_mode": "summary",
            "cache_hit": False,
            "summary_profile": summary_profile,
            "detected_intent": intent.intent,
            "intent_confidence": intent.confidence,
            "intent_route": "recursive_document_summary",
            "generation_backend": "recursive_extractive",
            "generation_error": None,
            "grounding_score": 1.0,
            "citation_count": len(citations),
            "context_chunks_used": len(citations),
            "grounding_state": "strong",
            "grounding_summary": "all readable chunks were reduced with original-source provenance",
            "document_overview_request": True,
            "context_relevance_state": "direct",
            "answer_relevance_state": "direct",
            "citation_verification_state": (
                "supported" if citation_support["cache_safe"] else "review"
            ),
            "cited_claims_checked": coverage["citation_sentence_count"],
            "unsupported_claims": [],
            "answer_rewritten_for_faithfulness": False,
            "answer_repair_mode": "none",
            "selected_context_chunk_ids": cited_chunk_ids,
            "cited_context_chunk_ids": cited_chunk_ids,
            "evidence_gate_passed": bool(citation_support["cache_safe"]),
            "summary_hierarchy": summary.metadata,
            "citation_support": citation_support,
            **coverage,
        }
        return QueryResponse(
            session_id=payload.session_id,
            answer=answer,
            citations=citations,
            grounded=bool(citation_support["cache_safe"]),
            retrieval_meta=retrieval_meta,
        )

    def _store_summary_if_applicable(
        self,
        *,
        payload: QueryRequest,
        retrieval_mode: str,
        retrieval_profile: str,
        intent: QueryIntent,
        answer: str,
        citations: list[Citation],
        retrieval_meta: dict[str, object],
    ) -> None:
        if not self._can_use_summary_cache(payload, intent):
            return
        document = self._sqlite_repo.get_document_by_id(str(payload.document_id))
        if not document:
            return
        summary_profile = self._summary_profile(
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
            query=payload.query,
        )
        cache_meta = {**retrieval_meta, "summary_profile": summary_profile}
        self._sqlite_repo.upsert_document_summary(
            summary_id=str(uuid4()),
            document_id=str(payload.document_id),
            content_hash=str(document["content_hash"]),
            summary_profile=summary_profile,
            answer=answer,
            citations_json=json.dumps([citation.model_dump() for citation in citations]),
            retrieval_meta_json=json.dumps(cache_meta),
        )

    def _persist_turn(
        self,
        *,
        session_id: str,
        query: str,
        answer: str,
        citations: list[Citation],
        retrieval_meta: dict[str, object],
    ) -> None:
        self._sqlite_repo.ensure_session(session_id)
        self._sqlite_repo.insert_message(str(uuid4()), session_id, "user", query)
        self._sqlite_repo.insert_message(
            str(uuid4()),
            session_id,
            "assistant",
            answer,
            citations_json=json.dumps([citation.model_dump() for citation in citations]),
            retrieval_meta_json=json.dumps(retrieval_meta),
        )

    @staticmethod
    def _can_use_summary_cache(payload: QueryRequest, intent: QueryIntent) -> bool:
        return bool(payload.document_id and intent.intent == "summary")

    @staticmethod
    def _summary_profile(*, retrieval_mode: str, retrieval_profile: str, query: str) -> str:
        normalized_query = re.sub(r"\s+", " ", query.strip().lower())
        scope_key = "document" if QueryService._is_document_wide_summary_query(query) else hashlib.sha1(
            normalized_query.encode("utf-8")
        ).hexdigest()[:12]
        return f"{retrieval_mode}:{retrieval_profile}:{RECURSIVE_SUMMARY_VERSION}:{scope_key}"

    @staticmethod
    def _is_document_wide_summary_query(query: str) -> bool:
        normalized = re.sub(r"\s+", " ", query.strip().lower())
        if re.search(
            r"\b(?:chapter|section|unit|module|part|pages?)\s+(?:\d+|[ivxlcdm]+\b)",
            normalized,
        ):
            return False
        if re.search(
            r"\bsummar(?:ize|ise|izing|ising)\s+(?:the\s+)?(?:abstract|introduction|methods?|methodology|results?|findings?|limitations?|conclusion)\b",
            normalized,
        ):
            return False
        document_terms = {
            "document",
            "pdf",
            "paper",
            "file",
            "textbook",
            "material",
            "notes",
            "source",
        }
        tokens = set(re.findall(r"[a-z]+", normalized))
        if tokens & document_terms:
            return True
        return len(tokens) <= 4 and bool(
            re.search(r"\b(?:summarize|summarise|summary|overview|explain)\b", normalized)
        )

    @staticmethod
    def _citations_from_synthesis_context(
        bundle: RetrievalBundle,
        synthesis_meta: dict[str, object],
        grounded: bool,
    ) -> list[Citation]:
        if not grounded:
            return []
        raw_chunk_ids = synthesis_meta.get("cited_context_chunk_ids")
        if not isinstance(raw_chunk_ids, list) or not raw_chunk_ids:
            return []

        cited_chunk_ids: list[str] = []
        seen: set[str] = set()
        for raw_chunk_id in raw_chunk_ids:
            chunk_id = str(raw_chunk_id)
            if not chunk_id or chunk_id in seen:
                continue
            cited_chunk_ids.append(chunk_id)
            seen.add(chunk_id)

        chunks_by_id = {chunk.chunk_id: chunk for chunk in bundle.chunks}
        cited_chunks = [
            chunks_by_id[chunk_id]
            for chunk_id in cited_chunk_ids
            if chunk_id in chunks_by_id
        ]
        return to_citations(cited_chunks)

    @staticmethod
    def _citation_source_rows(
        bundle: RetrievalBundle,
        citations: list[Citation],
        synthesis_meta: dict[str, object],
    ) -> list[dict[str, object]]:
        chunks_by_id = {chunk.chunk_id: chunk for chunk in bundle.chunks}
        anchor_map = synthesis_meta.get("citation_anchor_chunk_map")
        if isinstance(anchor_map, list):
            mapped_chunks: dict[int, str] = {}
            for item in anchor_map:
                if not isinstance(item, dict):
                    continue
                try:
                    anchor = int(item.get("anchor"))
                except (TypeError, ValueError):
                    continue
                chunk_id = str(item.get("chunk_id") or "")
                if anchor > 0 and chunk_id in chunks_by_id:
                    mapped_chunks[anchor] = chunk_id
            if mapped_chunks:
                return [
                    {"id": chunks_by_id[chunk_id].chunk_id, "text": chunks_by_id[chunk_id].text}
                    for _, chunk_id in sorted(mapped_chunks.items())
                ]
        return [
            {
                "id": citation.chunk_id,
                "text": chunks_by_id[citation.chunk_id].text,
            }
            for citation in citations
            if citation.chunk_id in chunks_by_id
        ]

    def _build_exam_context(self, payload: QueryRequest, intent: QueryIntent) -> dict[str, object]:
        if not payload.document_id:
            return {"questions": [], "diagrams": []}
        if not self._uses_exam_context(payload.mode, intent) and not self._is_diagram_request(payload.query):
            return {"questions": [], "diagrams": []}
        questions = self._sqlite_repo.list_question_bank_items(payload.document_id)[:12]
        diagrams = self._sqlite_repo.list_diagram_assets(payload.document_id)[:8]
        return {
            "questions": [
                {
                    "question": str(row["question"]),
                    "marks": row.get("marks"),
                    "source_label": row.get("source_label"),
                }
                for row in questions
            ],
            "diagrams": [
                {
                    "id": str(row["id"]),
                    "page_number": row.get("page_number"),
                    "caption": row.get("caption"),
                    "width": row.get("width"),
                    "height": row.get("height"),
                }
                for row in diagrams
            ],
        }

    @staticmethod
    def _retrieval_query(
        query: str,
        mode: str,
        exam_context: dict[str, object],
        intent: QueryIntent,
    ) -> str:
        normalized_query = query.strip().lower()
        if intent.intent == "summary" or (
            any(term in normalized_query for term in ("summarize", "summary", "overview"))
            and any(term in normalized_query for term in ("pdf", "document", "paper", "material", "file", "textbook"))
        ):
            return (
                f"{query}\n\n"
                "Document overview retrieval hints: abstract introduction conclusion summary methodology "
                "architecture approach contribution results limitations key points."
            )
        if intent.intent == "compare":
            # Side-specific evidence queries already carry the comparison plan.
            # Generic hints over-rank textbook roadmaps and backmatter indexes.
            return query
        if intent.intent == "paper_draft":
            return f"{query}\n\nPaper drafting retrieval hints: related work methodology results limitations future work citations."
        if intent.intent == "deep_research":
            return f"{query}\n\nDeep research retrieval hints: mechanism evidence caveats architecture results limitations implications."
        if intent.intent == "factual_lookup":
            # Keep retrieval centered on the user's subject. Generic answer-shape
            # words belong in synthesis and can dominate textbook index ranking.
            answer_plan = build_answer_plan(query=query, response_mode=mode)
            focused_query = answer_plan.evidence_query(query)
            subject_terms = QueryService._factual_category_expansion(focused_query)
            if subject_terms:
                return f"{focused_query}\n\nSubject expansion: {' '.join(subject_terms)}"
            return focused_query
        if mode.strip().lower() not in {"study_guide", "important_questions"}:
            return query
        questions = exam_context.get("questions", [])
        if not isinstance(questions, list) or not questions:
            return query
        question_text = " ".join(
            str(item.get("question", ""))
            for item in questions[:8]
            if isinstance(item, dict) and item.get("question")
        )
        if not question_text:
            return query
        return f"{query}\n\nImported questions:\n{question_text}"

    @staticmethod
    def _factual_category_expansion(query: str) -> list[str]:
        """Expand broad subject categories without adding answer-format noise."""
        normalized = query.lower()
        tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", normalized))
        if "unsupervised" in tokens and {"algorithm", "algorithms", "method", "methods"} & tokens:
            return [
                "unsupervised learning",
                "clustering",
                "density estimation",
                "anomaly detection",
                "dimensionality reduction",
                "pca",
            ]
        if "supervised" in tokens and {"algorithm", "algorithms", "method", "methods"} & tokens:
            return [
                "supervised learning",
                "classification",
                "regression",
                "labeled examples",
                "prediction",
            ]
        return []

    @staticmethod
    def _resolve_retrieval_mode(
        *,
        mode: str,
        retrieval_mode: str,
        document_id: str | None,
        intent: QueryIntent,
    ) -> str:
        direct_mode = retrieval_mode.strip().lower()
        if direct_mode in {"bm25", "vector"}:
            return direct_mode
        if direct_mode == "hybrid":
            if document_id and intent.intent in {
                "summary",
                "factual_lookup",
                "compare",
                "deep_research",
                "paper_draft",
                "exam",
            }:
                return "bm25"
            return "hybrid"
        legacy_mode = mode.strip().lower()
        if legacy_mode in {"hybrid", "bm25", "vector"}:
            return legacy_mode
        return "hybrid"

    @staticmethod
    def _resolve_retrieval_profile(requested_profile: str, intent: QueryIntent) -> str:
        normalized = requested_profile.strip().lower()
        if normalized not in {"fast", "balanced", "precision"}:
            normalized = "balanced"
        if normalized != "balanced":
            return normalized
        if intent.intent in {"paper_draft", "deep_research", "exam", "compare"}:
            return "precision"
        return normalized

    @staticmethod
    def _resolve_response_mode(requested_mode: str, intent: QueryIntent) -> str:
        normalized = requested_mode.strip().lower()
        if intent.intent == "summary":
            return "summary"
        if intent.intent == "compare":
            return "compare_concepts"
        if intent.intent == "paper_draft":
            return "research_paper"
        if intent.intent == "deep_research":
            return "deep_research"
        if intent.intent == "exam":
            return normalized if normalized in QueryService._exam_modes() else "exam_answer"
        if intent.intent == "general_chat":
            return "general_chat"
        if normalized == "summary":
            return "research"
        return normalized if normalized else "research"

    @staticmethod
    def _exam_modes() -> set[str]:
        return {
            "exam",
            "exam_answer",
            "revision_notes",
            "important_questions",
            "compare_concepts",
            "study_guide",
        }

    @staticmethod
    def _uses_exam_context(mode: str, intent: QueryIntent) -> bool:
        return intent.intent == "exam" or mode.strip().lower() in {
            "exam",
            "exam_answer",
            "revision_notes",
            "important_questions",
            "study_guide",
        }

    @staticmethod
    def _is_diagram_request(query: str) -> bool:
        visual = r"(?:diagram|diagrams|figure|figures|image|images|visual|visuals)"
        return bool(
            re.search(
                rf"\b(?:provide|include|show|add|cite|attach|use|with)\b.{{0,28}}\b{visual}\b",
                query,
                re.I,
            )
            or re.search(rf"\b{visual}\s+references?\b", query, re.I)
            or re.search(
                rf"\b(?:explain|describe|interpret|open)\s+(?:the\s+)?{visual}\b",
                query,
                re.I,
            )
            or re.search(rf"\bwhat\b.{{0,24}}\b{visual}\b.{{0,16}}\bshow", query, re.I)
        )

    def _augment_selected_summary_bundle(
        self,
        *,
        payload: QueryRequest,
        intent: QueryIntent,
        bundle: RetrievalBundle,
    ) -> RetrievalBundle:
        if not payload.document_id or intent.intent != "summary":
            return bundle
        rows = self._sqlite_repo.get_document_chunks(str(payload.document_id), active_only=True)
        if not rows:
            return bundle

        existing_ids = {chunk.chunk_id for chunk in bundle.chunks}
        summary_seeds, hierarchy_meta = select_hierarchical_summary_seeds(
            rows,
            max_seeds=8,
        )
        seed_chunks: list[RetrievedChunk] = []
        for rank, seed in enumerate(summary_seeds):
            row = seed.row
            chunk_id = str(row["id"])
            if chunk_id in existing_ids:
                continue
            seed_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(row["document_id"]),
                    text=str(row["text"]),
                    score=max(0.01, 0.12 - (rank * 0.005)),
                    page_start=row.get("page_start"),
                    page_end=row.get("page_end"),
                    source="hierarchical_summary_seed",
                    quality_score=float(row.get("quality_score") or 1.0),
                    section_id=row.get("section_id"),
                    heading=row.get("heading"),
                    section_path=row.get("section_path"),
                    chunk_type=str(row.get("chunk_type") or "body"),
                )
            )
            existing_ids.add(chunk_id)

        if not seed_chunks:
            return bundle
        return RetrievalBundle(
            chunks=[*seed_chunks, *bundle.chunks],
            meta={
                **bundle.meta,
                "summary_seed_chunks": len(seed_chunks),
                "summary_seed_strategy": "hierarchical_original_chunk_coverage",
                "summary_hierarchy": hierarchy_meta,
            },
        )
