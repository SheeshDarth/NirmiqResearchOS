from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.common import Citation


class SessionSummaryResponse(BaseModel):
    session_id: str
    summary: str
    message_count: int


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool
    deleted_messages: int
    deleted_snapshots: int


class SessionTimelineMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    citations: list[Citation] = Field(default_factory=list)
    retrieval_meta: dict[str, object] | None = None


class SessionTimelineResponse(BaseModel):
    session_id: str
    summary: str
    message_count: int
    latest_snapshot_created_at: datetime | None = None
    messages: list[SessionTimelineMessage]
