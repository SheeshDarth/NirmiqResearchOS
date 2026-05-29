from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.documents import (
    DocumentChunkItem,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
)


class DocumentsService:
    def __init__(self, sqlite_repo: SQLiteRepo) -> None:
        self._sqlite_repo = sqlite_repo

    async def list_documents(self) -> DocumentListResponse:
        rows = self._sqlite_repo.list_documents()
        items = [
            DocumentItem(
                id=row["id"],
                title=row.get("title"),
                status=row["status"],
                source_path=row["source_path"],
                active_chunk_count=int(row["active_chunk_count"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
        return DocumentListResponse(items=items)

    async def get_document(self, document_id: str) -> DocumentDetailResponse:
        row = self._sqlite_repo.get_document_by_id(document_id)
        if not row:
            raise ValueError(f"Document not found: {document_id}")
        chunks = [
            DocumentChunkItem(
                id=chunk["id"],
                document_id=chunk["document_id"],
                index_version=int(chunk["index_version"]),
                chunk_index=int(chunk["chunk_index"]),
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                text=chunk["text"],
                token_count=int(chunk["token_count"]),
                chunk_hash=chunk["chunk_hash"],
                is_active=bool(chunk["is_active"]),
                created_at=chunk["created_at"],
            )
            for chunk in self._sqlite_repo.get_document_chunks(document_id)
        ]
        return DocumentDetailResponse(
            id=row["id"],
            title=row.get("title"),
            status=row["status"],
            source_path=row["source_path"],
            active_chunk_count=self._sqlite_repo.get_active_chunk_count(document_id),
            updated_at=row["updated_at"],
            chunks=chunks,
        )
