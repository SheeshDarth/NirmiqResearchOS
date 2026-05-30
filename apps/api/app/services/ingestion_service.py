import hashlib
from pathlib import Path
import re
from uuid import uuid4

from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.ingest import (
    IngestJobsResponse,
    IngestionJobStatus,
    IngestRequest,
    IngestResponse,
    IngestStatusResponse,
)
from app.services.indexing_service import IndexingService


class IngestionService:
    _allowed_upload_extensions = {
        ".pdf",
        ".txt",
        ".md",
        ".markdown",
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".bmp",
        ".webp",
    }
    _max_upload_bytes = 75 * 1024 * 1024

    def __init__(
        self,
        sqlite_repo: SQLiteRepo,
        indexing_service: IndexingService,
        upload_root: Path,
    ) -> None:
        self._sqlite_repo = sqlite_repo
        self._indexing_service = indexing_service
        self._upload_root = upload_root

    async def ingest(self, payload: IngestRequest) -> IngestResponse:
        source = Path(payload.source_path).resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Source file not found: {source}")

        existing = self._sqlite_repo.get_document_by_source_path(str(source))
        current_hash = self._hash_file(source)
        if (
            existing
            and existing["content_hash"] == current_hash
            and existing["status"] == "indexed"
            and not payload.force_reindex
        ):
            return IngestResponse(document_id=existing["id"], status="indexed", indexed=True)

        document_id = existing["id"] if existing else str(uuid4())
        if not existing:
            self._sqlite_repo.insert_document(
                document_id=document_id,
                source_path=str(source),
                content_hash=current_hash,
                title=payload.title or source.stem,
                mime_type=payload.mime_type,
                status="uploaded",
            )
        else:
            self._sqlite_repo.update_document_metadata(
                document_id=document_id,
                content_hash=current_hash,
                title=payload.title or source.stem,
                mime_type=payload.mime_type,
            )
            self._sqlite_repo.mark_document_status(document_id=document_id, status="uploaded")

        job_id = str(uuid4())
        self._sqlite_repo.insert_ingestion_job(
            job_id=job_id, document_id=document_id, stage="indexing", status="running"
        )
        try:
            self._sqlite_repo.mark_document_status(document_id=document_id, status="parsed")
            await self._indexing_service.index_document(document_id)
        except Exception as exc:
            self._sqlite_repo.mark_document_status(document_id=document_id, status="failed")
            self._sqlite_repo.update_ingestion_job(
                job_id=job_id, stage="indexing", status="failed", error=str(exc)
            )
            raise

        self._sqlite_repo.update_ingestion_job(
            job_id=job_id, stage="indexing", status="completed", error=None
        )
        return IngestResponse(document_id=document_id, status="indexed", indexed=True)

    async def ingest_upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
        title: str | None = None,
        force_reindex: bool = False,
    ) -> IngestResponse:
        if not content:
            raise ValueError("Uploaded file is empty.")
        if len(content) > self._max_upload_bytes:
            raise ValueError("Uploaded file is too large. Maximum supported size is 75 MB.")

        source = self._write_upload(filename=filename, content=content)
        return await self.ingest(
            IngestRequest(
                source_path=str(source),
                title=title or source.stem,
                mime_type=content_type,
                force_reindex=force_reindex,
            )
        )

    async def get_status(self, document_id: str) -> IngestStatusResponse:
        document = self._sqlite_repo.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        chunk_count = self._sqlite_repo.get_active_chunk_count(document_id)
        latest_job = self._sqlite_repo.get_latest_ingestion_job(document_id)
        job_payload = (
            IngestionJobStatus(
                stage=str(latest_job["stage"]),
                status=str(latest_job["status"]),
                error=str(latest_job["error"]) if latest_job.get("error") is not None else None,
                started_at=str(latest_job["started_at"]),
                finished_at=(
                    str(latest_job["finished_at"]) if latest_job.get("finished_at") is not None else None
                ),
            )
            if latest_job
            else None
        )
        return IngestStatusResponse(
            document_id=document_id,
            status=str(document["status"]),
            source_path=str(document["source_path"]),
            title=str(document["title"]) if document.get("title") is not None else None,
            active_chunk_count=chunk_count,
            latest_job=job_payload,
        )

    async def get_jobs(self, document_id: str) -> IngestJobsResponse:
        document = self._sqlite_repo.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        jobs = self._sqlite_repo.get_ingestion_jobs(document_id)
        return IngestJobsResponse(
            document_id=document_id,
            jobs=[
                IngestionJobStatus(
                    stage=str(job["stage"]),
                    status=str(job["status"]),
                    error=str(job["error"]) if job.get("error") is not None else None,
                    started_at=str(job["started_at"]),
                    finished_at=str(job["finished_at"]) if job.get("finished_at") is not None else None,
                )
                for job in jobs
            ],
        )

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _write_upload(self, *, filename: str, content: bytes) -> Path:
        original = Path(filename or "upload").name
        suffix = Path(original).suffix.lower()
        if suffix not in self._allowed_upload_extensions:
            allowed = ", ".join(sorted(self._allowed_upload_extensions))
            raise ValueError(f"Unsupported upload type '{suffix or 'unknown'}'. Allowed: {allowed}")

        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(original).stem).strip(".-")
        safe_stem = safe_stem[:80] or "upload"
        self._upload_root.mkdir(parents=True, exist_ok=True)
        target = self._upload_root / f"{safe_stem}-{uuid4().hex[:10]}{suffix}"
        target.write_bytes(content)
        return target.resolve()
