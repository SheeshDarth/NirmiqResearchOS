import json
from uuid import uuid4

from app.api.schemas.common import Citation
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.query import QueryRequest, QueryResponse
from app.domain.citations import to_citations
from app.domain.query_intent import QueryIntent, detect_query_intent
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
        retrieval_mode = self._resolve_retrieval_mode(payload.mode, payload.retrieval_mode)
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

        exam_context = self._build_exam_context(payload)
        retrieval_query = self._retrieval_query(payload.query, payload.mode, exam_context, intent)
        bundle = await self._retrieval_service.retrieve_with_mode(
            retrieval_query,
            mode=retrieval_mode,
            document_id=payload.document_id,
            profile=retrieval_profile,
        )
        answer, grounded, synthesis_meta = await self._synthesis_service.synthesize(
            payload.query,
            bundle,
            response_mode=payload.mode,
            exam_profile=payload.exam_profile.model_dump() if payload.exam_profile else None,
            exam_context=exam_context,
        )
        citations = to_citations(bundle.chunks)
        combined_meta = {
            **bundle.meta,
            **synthesis_meta,
            "requested_retrieval_mode": retrieval_mode,
            "retrieval_query_expanded": retrieval_query != payload.query,
            "requested_retrieval_profile": payload.retrieval_profile,
            "effective_retrieval_profile": retrieval_profile,
            "response_mode": payload.mode,
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
        )
        cached = self._sqlite_repo.get_document_summary(
            document_id=str(payload.document_id),
            content_hash=str(document["content_hash"]),
            summary_profile=summary_profile,
        )
        if not cached:
            return None
        citations = [
            Citation.model_validate(item)
            for item in json.loads(str(cached["citations_json"]) or "[]")
        ]
        retrieval_meta = json.loads(str(cached["retrieval_meta_json"]) or "{}")
        retrieval_meta.update(
            {
                "cache_hit": True,
                "detected_intent": intent.intent,
                "intent_confidence": intent.confidence,
                "intent_route": "summary_cache_hit",
                "requested_retrieval_mode": retrieval_mode,
                "requested_retrieval_profile": payload.retrieval_profile,
                "effective_retrieval_profile": retrieval_profile,
                "summary_profile": summary_profile,
            }
        )
        return QueryResponse(
            session_id=payload.session_id,
            answer=str(cached["answer"]),
            citations=citations,
            grounded=True,
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
    def _summary_profile(*, retrieval_mode: str, retrieval_profile: str) -> str:
        return f"{retrieval_mode}:{retrieval_profile}:v1"

    def _build_exam_context(self, payload: QueryRequest) -> dict[str, object]:
        if not payload.document_id or not self._uses_exam_context(payload.mode):
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
                    "page_number": row.get("page_number"),
                    "image_path": str(row["image_path"]),
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
        normalized_mode = mode.strip().lower()
        normalized_query = query.strip().lower()
        if intent.intent == "summary" or normalized_mode == "summary" or (
            any(term in normalized_query for term in ("summarize", "summary", "overview", "explain"))
            and any(term in normalized_query for term in ("pdf", "document", "paper", "material", "file", "this"))
        ):
            return (
                f"{query}\n\n"
                "Document overview retrieval hints: abstract introduction conclusion summary methodology "
                "architecture approach contribution results limitations key points."
            )
        if intent.intent == "compare":
            return f"{query}\n\nComparison retrieval hints: differences similarities contrast tradeoffs advantages limitations."
        if intent.intent == "paper_draft":
            return f"{query}\n\nPaper drafting retrieval hints: related work methodology results limitations future work citations."
        if intent.intent == "deep_research":
            return f"{query}\n\nDeep research retrieval hints: mechanism evidence caveats architecture results limitations implications."
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
    def _resolve_retrieval_mode(mode: str, retrieval_mode: str) -> str:
        direct_mode = retrieval_mode.strip().lower()
        if direct_mode in {"hybrid", "bm25", "vector"}:
            return direct_mode
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
    def _uses_exam_context(mode: str) -> bool:
        return mode.strip().lower() in {
            "exam_answer",
            "revision_notes",
            "important_questions",
            "study_guide",
        }
