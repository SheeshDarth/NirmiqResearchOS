from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.adapters.storage.chroma_repo import ChromaRepo
from app.api.schemas.documents import (
    DocumentChunkItem,
    DocumentDeleteResponse,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
)


class DocumentsService:
    def __init__(self, sqlite_repo: SQLiteRepo, chroma_repo: ChromaRepo) -> None:
        self._sqlite_repo = sqlite_repo
        self._chroma_repo = chroma_repo

    async def list_documents(self) -> DocumentListResponse:
        rows = self._sqlite_repo.list_documents()
        items = [
            DocumentItem(
                id=row["id"],
                title=row.get("title"),
                status=self._display_status(row["status"], int(row["active_chunk_count"])),
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

    async def delete_document(self, document_id: str) -> DocumentDeleteResponse:
        deleted = self._sqlite_repo.delete_document(document_id)
        if not deleted:
            raise ValueError(f"Document not found: {document_id}")
        await self._chroma_repo.delete_document(document_id)
        return DocumentDeleteResponse(document_id=document_id, deleted=True)

    @staticmethod
    def _display_status(status: str, active_chunk_count: int) -> str:
        if status == "indexed" and active_chunk_count <= 0:
            return "needs_reindex"
        if status == "failed" and active_chunk_count > 0:
            return "needs_reindex"
        return status
