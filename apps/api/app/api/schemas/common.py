from datetime import datetime

from pydantic import BaseModel


class APIMessage(BaseModel):
    detail: str


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    page_start: int | None = None
    page_end: int | None = None
    score: float | None = None
    excerpt: str | None = None


class TimestampedModel(BaseModel):
    created_at: datetime
