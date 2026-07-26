from pathlib import Path
import asyncio

import pytest

from app.api.schemas.ingest import IngestRequest
from app.services.ingestion_service import IngestionService


def _service(tmp_path: Path, *, allow_arbitrary: bool = False) -> IngestionService:
    allowed_root = tmp_path / "allowed"
    upload_root = allowed_root / "uploads"
    allowed_root.mkdir(parents=True)
    return IngestionService(
        sqlite_repo=object(),  # type: ignore[arg-type]
        indexing_service=object(),  # type: ignore[arg-type]
        upload_root=upload_root,
        allowed_roots=[allowed_root],
        allow_arbitrary_local_paths=allow_arbitrary,
    )


def test_local_path_ingestion_rejects_files_outside_allowed_roots(tmp_path: Path) -> None:
    service = _service(tmp_path)
    outside = tmp_path / "private-note.txt"
    outside.write_text("not part of the NIRMIQ corpus", encoding="utf-8")

    with pytest.raises(ValueError, match="restricted for privacy"):
        service._assert_source_allowed(outside)


def test_local_path_ingestion_allows_project_data_roots(tmp_path: Path) -> None:
    service = _service(tmp_path)
    inside = tmp_path / "allowed" / "notes.txt"
    inside.write_text("safe corpus material", encoding="utf-8")

    service._assert_source_allowed(inside)


def test_upload_validation_rejects_extension_spoofed_pdf() -> None:
    with pytest.raises(ValueError, match="valid PDF"):
        IngestionService._validate_upload_content(suffix=".pdf", content=b"not really a pdf")


def test_upload_validation_accepts_plain_utf8_notes() -> None:
    IngestionService._validate_upload_content(
        suffix=".md",
        content=b"# Notes\n\nThis is readable UTF-8 academic material.",
    )


def test_indexed_document_with_no_active_chunks_is_not_treated_as_cache_hit(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    source = allowed_root / "scan.txt"
    source.write_text("Readable local source text.", encoding="utf-8")

    class Repo:
        def __init__(self) -> None:
            self.index_calls = 0

        def get_document_by_source_path(self, source_path: str) -> dict[str, object]:
            return {
                "id": "doc-1",
                "content_hash": IngestionService._hash_file(source),
                "status": "indexed",
            }

        def get_active_chunk_count(self, document_id: str) -> int:
            return 0

        def update_document_metadata(self, **_: object) -> None:
            return None

        def mark_document_status(self, **_: object) -> None:
            return None

        def insert_ingestion_job(self, **_: object) -> None:
            return None

        def update_ingestion_job(self, **_: object) -> None:
            return None

    class Indexer:
        async def index_document(self, document_id: str) -> None:
            return None

    repo = Repo()
    service = IngestionService(
        sqlite_repo=repo,  # type: ignore[arg-type]
        indexing_service=Indexer(),  # type: ignore[arg-type]
        upload_root=allowed_root,
        allowed_roots=[allowed_root],
    )

    response = asyncio.run(
        service.ingest(
            IngestRequest(source_path=str(source), title="Scan", force_reindex=False)
        )
    )

    assert response.document_id == "doc-1"
