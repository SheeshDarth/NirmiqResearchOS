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


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool


class DocumentPurgeResponse(BaseModel):
    deleted_count: int
    deleted_document_ids: list[str]
    vector_store_cleared: bool
    source_files_deleted: bool = False
    source_file_delete_count: int = 0
    derived_files_deleted: int = 0
    note: str


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
    section_id: str | None = None
    heading: str | None = None
    section_path: str | None = None
    chunk_type: str | None = None
    key_terms_json: str | None = None
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
