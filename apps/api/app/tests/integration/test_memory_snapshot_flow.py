from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_memory_snapshot_created_after_multiple_turns(tmp_path: Path) -> None:
    sample = tmp_path / "memory_sample.txt"
    sample.write_text(
        "NIRMIQ memory testing document. It captures retrieval and continuity requirements.",
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

        for idx in range(3):
            response = client.post(
                "/query",
                json={
                    "session_id": session_id,
                    "query": f"What does this document say about continuity? turn {idx}",
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

