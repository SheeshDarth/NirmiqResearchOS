from fastapi import APIRouter, Depends, Response

from app.api.schemas.memory import (
    AnswerFeedbackItem,
    AnswerFeedbackListResponse,
    AnswerFeedbackRequest,
    SessionDeleteResponse,
    SessionPurgeResponse,
    SessionSummaryResponse,
    SessionTimelineResponse,
)
from app.core.deps import get_memory_service
from app.services.memory_service import MemoryService

router = APIRouter()


@router.delete("", response_model=SessionPurgeResponse)
async def purge_sessions(
    service: MemoryService = Depends(get_memory_service),
) -> SessionPurgeResponse:
    return await service.purge_sessions()


@router.get("/{session_id}", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> SessionSummaryResponse:
    return await service.get_summary(session_id)


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> Response:
    markdown = await service.export_markdown(session_id)
    safe_session_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in session_id)[:80]
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="nirmiq-thread-{safe_session_id}.md"'},
    )


@router.get("/{session_id}/timeline", response_model=SessionTimelineResponse)
async def get_session_timeline(
    session_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> SessionTimelineResponse:
    return await service.get_timeline(session_id)


@router.post("/{session_id}/feedback", response_model=AnswerFeedbackItem)
async def save_answer_feedback(
    session_id: str,
    payload: AnswerFeedbackRequest,
    service: MemoryService = Depends(get_memory_service),
) -> AnswerFeedbackItem:
    return await service.save_answer_feedback(session_id, payload)


@router.get("/{session_id}/feedback", response_model=AnswerFeedbackListResponse)
async def list_answer_feedback(
    session_id: str,
    limit: int = 50,
    service: MemoryService = Depends(get_memory_service),
) -> AnswerFeedbackListResponse:
    return await service.list_answer_feedback(session_id, limit=limit)


@router.delete("/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(
    session_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> SessionDeleteResponse:
    return await service.delete_session(session_id)
