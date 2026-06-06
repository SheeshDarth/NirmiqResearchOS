import json
from pathlib import Path

from app.adapters.storage.sqlite_repo import SQLiteRepo


def test_document_summary_cache_roundtrip_and_delete(tmp_path: Path) -> None:
    repo = SQLiteRepo(tmp_path / "nirmiq.db")
    repo.init_db()
    repo.insert_document(
        document_id="doc-1",
        source_path=str(tmp_path / "source.txt"),
        content_hash="hash-1",
        title="Source",
        mime_type="text/plain",
        status="indexed",
    )

    repo.upsert_document_summary(
        summary_id="summary-1",
        document_id="doc-1",
        content_hash="hash-1",
        summary_profile="bm25:balanced:v1",
        answer="Document summary from the retrieved passages.",
        citations_json=json.dumps([]),
        retrieval_meta_json=json.dumps({"cache_hit": False}),
    )

    cached = repo.get_document_summary(
        document_id="doc-1",
        content_hash="hash-1",
        summary_profile="bm25:balanced:v1",
    )
    assert cached is not None
    assert cached["answer"].startswith("Document summary")
    assert repo.get_document_summary_count("doc-1") == 1

    assert repo.get_document_summary(
        document_id="doc-1",
        content_hash="hash-2",
        summary_profile="bm25:balanced:v1",
    ) is None

    assert repo.delete_document("doc-1") is True
    assert repo.get_document_summary_count("doc-1") == 0
