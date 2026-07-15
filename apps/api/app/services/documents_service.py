import shutil
from pathlib import Path

from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.adapters.storage.chroma_repo import ChromaRepo
from app.api.schemas.documents import (
    DocumentChunkItem,
    DocumentDeleteResponse,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
    DocumentPurgeResponse,
)


class DocumentsService:
    def __init__(
        self,
        sqlite_repo: SQLiteRepo,
        chroma_repo: ChromaRepo,
        *,
        workspace_root: Path,
        parse_cache_path: Path,
        upload_root: Path,
        diagram_root: Path,
    ) -> None:
        self._sqlite_repo = sqlite_repo
        self._chroma_repo = chroma_repo
        self._workspace_root = workspace_root.resolve()
        self._parse_cache_path = parse_cache_path.resolve()
        self._upload_root = upload_root.resolve()
        self._diagram_root = diagram_root.resolve()

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
                section_id=chunk.get("section_id"),
                heading=chunk.get("heading"),
                section_path=chunk.get("section_path"),
                chunk_type=chunk.get("chunk_type"),
                key_terms_json=chunk.get("key_terms_json"),
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
        document = self._sqlite_repo.get_document_by_id(document_id)
        deleted = self._sqlite_repo.delete_document(document_id)
        if not deleted:
            raise ValueError(f"Document not found: {document_id}")
        await self._chroma_repo.delete_document(document_id)
        if document:
            self._delete_owned_artifacts([document], delete_uploaded_sources=True)
        return DocumentDeleteResponse(document_id=document_id, deleted=True)

    async def purge_documents(self) -> DocumentPurgeResponse:
        document_rows = [
            row
            for item in self._sqlite_repo.list_documents()
            if (row := self._sqlite_repo.get_document_by_id(str(item["id"])))
        ]
        deleted_document_ids = self._sqlite_repo.delete_all_documents()
        vector_store_cleared = await self._chroma_repo.clear_all_documents()
        artifact_counts = self._delete_owned_artifacts(document_rows, delete_uploaded_sources=True)
        artifact_counts["source_files"] += self._clear_owned_root(self._upload_root)
        artifact_counts["derived_files"] += self._clear_owned_root(self._parse_cache_path)
        artifact_counts["derived_files"] += self._clear_owned_root(self._diagram_root)
        return DocumentPurgeResponse(
            deleted_count=len(deleted_document_ids),
            deleted_document_ids=deleted_document_ids,
            vector_store_cleared=vector_store_cleared,
            source_files_deleted=artifact_counts["source_files"] > 0,
            source_file_delete_count=artifact_counts["source_files"],
            derived_files_deleted=artifact_counts["derived_files"],
            note=(
                "Cleared NIRMIQ document metadata, chunks, jobs, summaries, exam artifacts, "
                "vector entries, parse cache files, extracted diagrams, and app-owned uploaded source copies. "
                "External local-path source files outside the upload directory were not deleted."
            ),
        )

    def _delete_owned_artifacts(
        self,
        document_rows: list[dict[str, object]],
        *,
        delete_uploaded_sources: bool,
    ) -> dict[str, int]:
        source_file_delete_count = 0
        derived_file_delete_count = 0
        for row in document_rows:
            document_id = str(row.get("id") or "")
            content_hash = str(row.get("content_hash") or "")
            source_path = Path(str(row.get("source_path") or ""))

            if document_id:
                diagram_dir = self._diagram_root / document_id
                if self._is_safe_child(diagram_dir, self._diagram_root) and diagram_dir.exists():
                    derived_file_delete_count += self._count_files(diagram_dir)
                    shutil.rmtree(diagram_dir, ignore_errors=True)

            if content_hash:
                cache_file = self._parse_cache_path / f"{content_hash}.v1.json"
                if self._is_safe_child(cache_file, self._parse_cache_path) and cache_file.exists():
                    cache_file.unlink(missing_ok=True)
                    derived_file_delete_count += 1

            if delete_uploaded_sources and source_path:
                try:
                    resolved_source = source_path.resolve()
                except OSError:
                    continue
                if self._is_safe_child(resolved_source, self._upload_root) and resolved_source.is_file():
                    resolved_source.unlink(missing_ok=True)
                    source_file_delete_count += 1

        return {"source_files": source_file_delete_count, "derived_files": derived_file_delete_count}

    def _clear_owned_root(self, root: Path) -> int:
        """Delete orphaned app-owned files without ever traversing outside the workspace."""
        if root == self._workspace_root or not self._is_safe_child(root, self._workspace_root):
            return 0
        if not root.exists() or not root.is_dir():
            return 0

        deleted_files = 0
        for child in list(root.iterdir()):
            file_count = 1 if child.is_symlink() else self._count_files(child)
            try:
                if child.is_symlink() or child.is_file():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    shutil.rmtree(child)
            except OSError:
                continue
            if not child.exists():
                deleted_files += file_count
        return deleted_files

    @staticmethod
    def _is_safe_child(path: Path, root: Path) -> bool:
        try:
            resolved_path = path.resolve()
            resolved_root = root.resolve()
        except OSError:
            return False
        return resolved_path == resolved_root or resolved_root in resolved_path.parents

    @staticmethod
    def _count_files(path: Path) -> int:
        if path.is_file():
            return 1
        if not path.exists():
            return 0
        return sum(1 for child in path.rglob("*") if child.is_file())

    @staticmethod
    def _display_status(status: str, active_chunk_count: int) -> str:
        if status == "indexed" and active_chunk_count <= 0:
            return "needs_reindex"
        if status == "failed" and active_chunk_count > 0:
            return "needs_reindex"
        return status
