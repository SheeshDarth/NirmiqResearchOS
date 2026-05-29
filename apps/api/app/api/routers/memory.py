from fastapi import APIRouter, Depends

from app.api.schemas.memory import SessionSummaryResponse, SessionTimelineResponse
from app.core.deps import get_memory_service
from app.services.memory_service import MemoryService

router = APIRouter()


@router.get("/{session_id}", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> SessionSummaryResponse:
    return await service.get_summary(session_id)


@router.get("/{session_id}/timeline", response_model=SessionTimelineResponse)
async def get_session_timeline(
    session_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> SessionTimelineResponse:
    return await service.get_timeline(session_id)
