from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.common import Citation


class QueryRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    document_id: str | None = None
    mode: str = "research"
    retrieval_profile: Literal["fast", "balanced", "precision"] = "balanced"
    retrieval_mode: Literal["hybrid", "bm25", "vector"] = "hybrid"
    debug: bool = False


class QueryResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    grounded: bool
    retrieval_meta: dict[str, object] | None = None
