from pathlib import Path

import pytest

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
