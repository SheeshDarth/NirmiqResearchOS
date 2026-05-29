import json
from uuid import uuid4

from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.query import QueryRequest, QueryResponse
from app.domain.citations import to_citations
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
        retrieval_mode = self._resolve_retrieval_mode(payload.mode, payload.retrieval_mode)
        exam_context = self._build_exam_context(payload)
        retrieval_query = self._retrieval_query(payload.query, payload.mode, exam_context)
        bundle = await self._retrieval_service.retrieve_with_mode(
            retrieval_query,
            mode=retrieval_mode,
            document_id=payload.document_id,
            profile=payload.retrieval_profile,
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
            "response_mode": payload.mode,
            "exam_profile": payload.exam_profile.model_dump() if payload.exam_profile else None,
            "exam_context": {
                "question_count": len(exam_context.get("questions", [])),
                "diagram_count": len(exam_context.get("diagrams", [])),
            },
        }

        if persist:
            self._sqlite_repo.ensure_session(payload.session_id)
            self._sqlite_repo.insert_message(str(uuid4()), payload.session_id, "user", payload.query)
            self._sqlite_repo.insert_message(
                str(uuid4()),
                payload.session_id,
                "assistant",
                answer,
                citations_json=json.dumps([citation.model_dump() for citation in citations]),
                retrieval_meta_json=json.dumps(combined_meta),
            )
            await self._memory_service.maybe_refresh_snapshot(payload.session_id)

        return QueryResponse(
            session_id=payload.session_id,
            answer=answer,
            citations=citations,
            grounded=grounded,
            retrieval_meta=combined_meta if payload.debug else None,
        )

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
    def _retrieval_query(query: str, mode: str, exam_context: dict[str, object]) -> str:
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
    def _uses_exam_context(mode: str) -> bool:
        return mode.strip().lower() in {
            "exam_answer",
            "revision_notes",
            "important_questions",
            "study_guide",
        }
