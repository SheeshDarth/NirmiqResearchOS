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
        bundle = await self._retrieval_service.retrieve_with_mode(
            payload.query,
            mode=retrieval_mode,
            document_id=payload.document_id,
            profile=payload.retrieval_profile,
        )
        answer, grounded, synthesis_meta = await self._synthesis_service.synthesize(
            payload.query, bundle, response_mode=payload.mode
        )
        citations = to_citations(bundle.chunks)
        combined_meta = {
            **bundle.meta,
            **synthesis_meta,
            "requested_retrieval_mode": retrieval_mode,
            "requested_retrieval_profile": payload.retrieval_profile,
            "response_mode": payload.mode,
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

    @staticmethod
    def _resolve_retrieval_mode(mode: str, retrieval_mode: str) -> str:
        direct_mode = retrieval_mode.strip().lower()
        if direct_mode in {"hybrid", "bm25", "vector"}:
            return direct_mode
        legacy_mode = mode.strip().lower()
        if legacy_mode in {"hybrid", "bm25", "vector"}:
            return legacy_mode
        return "hybrid"
