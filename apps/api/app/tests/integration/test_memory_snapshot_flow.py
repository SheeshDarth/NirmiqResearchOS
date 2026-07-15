from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_memory_snapshot_created_after_multiple_turns(tmp_path: Path) -> None:
    sample = tmp_path / "memory_sample.txt"
    sample.write_text(
        (
            "NIRMIQ memory testing captures local retrieval requirements and session continuity requirements. "
            "Retrieval finds relevant source passages. Session continuity keeps the current research conversation "
            "available for follow-up questions. Both capabilities operate locally so document evidence remains "
            "on the user device."
        ),
        encoding="utf-8",
    )

    session_id = "memory-session"
    with TestClient(app) as client:
        ingest_response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Memory Sample",
                "mime_type": "text/plain",
            },
        )
        assert ingest_response.status_code == 200
        document_id = ingest_response.json()["document_id"]

        for _ in range(3):
            response = client.post(
                "/query",
                json={
                    "session_id": session_id,
                    "query": "What does NIRMIQ memory testing capture?",
                    "document_id": document_id,
                    "debug": True,
                },
            )
            assert response.status_code == 200
            assert response.json()["grounded"] is True

        memory_response = client.get(f"/memory/{session_id}")
        assert memory_response.status_code == 200
        body = memory_response.json()
        assert body["message_count"] >= 6
        assert body["summary"] != "No memory summary yet."

        purge_response = client.delete("/memory")
        assert purge_response.status_code == 200
        purge_body = purge_response.json()
        assert purge_body["deleted_sessions"] >= 1
        assert purge_body["deleted_messages"] >= 6
        assert purge_body["deleted_snapshots"] >= 1

        empty_timeline = client.get(f"/memory/{session_id}/timeline")
        assert empty_timeline.status_code == 200
        assert empty_timeline.json()["message_count"] == 0

        alias_response = client.delete("/api/v1/memory")
        assert alias_response.status_code == 200
        assert alias_response.json()["deleted_sessions"] == 0
