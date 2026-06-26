from pathlib import Path

from app.adapters.storage.sqlite_repo import SQLiteRepo


def test_answer_feedback_roundtrip_and_session_delete(tmp_path: Path) -> None:
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

    saved = repo.insert_answer_feedback(
        feedback_id="feedback-1",
        session_id="session-1",
        rating="needs_work",
        query="Explain clustering.",
        answer="The answer was too broad.",
        document_id="doc-1",
        source_title="Source",
        reason="missing_key_points",
    )

    assert saved["id"] == "feedback-1"
    assert saved["rating"] == "needs_work"
    assert repo.get_answer_feedback_count("session-1") == 1
    listed = repo.list_answer_feedback("session-1")
    assert len(listed) == 1
    assert listed[0]["query"] == "Explain clustering."

    deleted = repo.delete_session("session-1")
    assert deleted["deleted"] is True
    assert repo.get_answer_feedback_count("session-1") == 0


def test_answer_feedback_keeps_review_signal_when_document_deleted(tmp_path: Path) -> None:
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
    repo.insert_answer_feedback(
        feedback_id="feedback-1",
        session_id="session-1",
        rating="good",
        query="Summarize.",
        answer="Useful answer.",
        document_id="doc-1",
        source_title="Source",
        reason="helpful_answer",
    )

    assert repo.delete_document("doc-1") is True
    listed = repo.list_answer_feedback("session-1")
    assert listed[0]["document_id"] is None
    assert listed[0]["source_title"] == "Source"
