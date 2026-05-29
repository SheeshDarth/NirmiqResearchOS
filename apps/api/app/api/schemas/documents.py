from pydantic import BaseModel


class DocumentItem(BaseModel):
    id: str
    title: str | None = None
    status: str
    source_path: str
    active_chunk_count: int
    updated_at: str


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]


class DocumentChunkItem(BaseModel):
    id: str
    document_id: str
    index_version: int
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    text: str
    token_count: int
    chunk_hash: str
    is_active: bool
    created_at: str


class DocumentDetailResponse(BaseModel):
    id: str
    title: str | None = None
    status: str
    source_path: str
    active_chunk_count: int
    updated_at: str
    chunks: list[DocumentChunkItem]
