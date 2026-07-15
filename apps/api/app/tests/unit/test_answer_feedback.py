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


def test_delete_all_sessions_removes_session_owned_data(tmp_path: Path) -> None:
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
    repo.ensure_session("session-1")
    repo.insert_message("message-1", "session-1", "user", "Explain clustering.")
    repo.insert_memory_snapshot("snapshot-1", "session-1", "Clustering notes", None, "message-1")
    repo.insert_answer_feedback(
        feedback_id="feedback-1",
        session_id="session-1",
        rating="good",
        query="Explain clustering.",
        answer="A grounded answer.",
        document_id="doc-1",
        source_title="Source",
    )
    repo.upsert_exam_profile(
        profile_id="profile-1",
        session_id="session-1",
        document_id="doc-1",
        title="Exam profile",
        marks=10,
        answer_style="structured",
        content_type="text",
        instructions=None,
    )

    result = repo.delete_all_sessions()

    assert result == {
        "deleted_sessions": 1,
        "deleted_messages": 1,
        "deleted_snapshots": 1,
        "deleted_feedback": 1,
        "deleted_exam_profiles": 1,
    }
    assert repo.get_session_message_count("session-1") == 0
    assert repo.get_latest_memory_snapshot("session-1") is None
    assert repo.get_answer_feedback_count("session-1") == 0
    assert repo.list_exam_profiles("session-1") == []
    assert repo.delete_all_sessions() == {
        "deleted_sessions": 0,
        "deleted_messages": 0,
        "deleted_snapshots": 0,
        "deleted_feedback": 0,
        "deleted_exam_profiles": 0,
    }
