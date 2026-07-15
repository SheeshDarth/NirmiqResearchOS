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


class SessionPurgeResponse(BaseModel):
    deleted_sessions: int
    deleted_messages: int
    deleted_snapshots: int
    deleted_feedback: int
    deleted_exam_profiles: int


class AnswerFeedbackRequest(BaseModel):
    rating: Literal["good", "needs_work"]
    query: str = Field(..., min_length=1, max_length=4000)
    answer: str = Field(..., min_length=1, max_length=20000)
    document_id: str | None = Field(default=None, max_length=160)
    source_title: str | None = Field(default=None, max_length=300)
    reason: str | None = Field(default=None, max_length=500)


class AnswerFeedbackItem(BaseModel):
    id: str
    session_id: str
    rating: Literal["good", "needs_work"]
    query: str
    answer: str
    document_id: str | None = None
    source_title: str | None = None
    reason: str | None = None
    created_at: datetime


class AnswerFeedbackListResponse(BaseModel):
    session_id: str
    items: list[AnswerFeedbackItem]


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
