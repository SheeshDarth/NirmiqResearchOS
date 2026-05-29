from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.common import Citation


class ExamAnswerSettings(BaseModel):
    marks: int = Field(default=10, ge=1, le=100)
    answer_style: str = "exam-ready"
    content_type: str = "conceptual"
    instructions: str | None = None


class QueryRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    document_id: str | None = None
    mode: str = "research"
    retrieval_profile: Literal["fast", "balanced", "precision"] = "balanced"
    retrieval_mode: Literal["hybrid", "bm25", "vector"] = "hybrid"
    exam_profile: ExamAnswerSettings | None = None
    debug: bool = False


class QueryResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    grounded: bool
    retrieval_meta: dict[str, object] | None = None
