from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source_path: str = Field(..., min_length=1)
    title: str | None = None
    mime_type: str | None = None
    force_reindex: bool = False


class IngestResponse(BaseModel):
    document_id: str
    status: str
    indexed: bool


class IngestionJobStatus(BaseModel):
    stage: str
    status: str
    error: str | None = None
    started_at: str
    finished_at: str | None = None


class IngestStatusResponse(BaseModel):
    document_id: str
    status: str
    source_path: str
    title: str | None = None
    active_chunk_count: int
    latest_job: IngestionJobStatus | None = None


class IngestJobsResponse(BaseModel):
    document_id: str
    jobs: list[IngestionJobStatus]
