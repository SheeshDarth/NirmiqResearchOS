from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_ingest_and_query_roundtrip(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text(
        (
            "NIRMIQ focuses on offline-first research workflows. "
            "It uses local retrieval and grounded synthesis with citations."
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        ingest_response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Sample",
                "mime_type": "text/plain",
            },
        )
        assert ingest_response.status_code == 200
        document_id = ingest_response.json()["document_id"]

        ingest_status = client.get(f"/ingest/{document_id}")
        assert ingest_status.status_code == 200
        status_body = ingest_status.json()
        assert status_body["document_id"] == document_id
        assert status_body["status"] == "indexed"
        assert status_body["active_chunk_count"] >= 1
        assert status_body["latest_job"] is not None
        assert status_body["latest_job"]["status"] in {"running", "completed"}

        ingest_jobs = client.get(f"/ingest/{document_id}/jobs")
        assert ingest_jobs.status_code == 200
        jobs_body = ingest_jobs.json()
        assert jobs_body["document_id"] == document_id
        assert len(jobs_body["jobs"]) >= 1
        assert jobs_body["jobs"][0]["stage"] == "indexing"

        docs_response = client.get("/documents")
        assert docs_response.status_code == 200
        doc_ids = [item["id"] for item in docs_response.json()["items"]]
        assert document_id in doc_ids

        document_detail = client.get(f"/documents/{document_id}")
        assert document_detail.status_code == 200
        detail_body = document_detail.json()
        assert detail_body["id"] == document_id
        assert detail_body["active_chunk_count"] >= 1
        assert len(detail_body["chunks"]) >= 1
        assert detail_body["chunks"][0]["document_id"] == document_id

        query_response = client.post(
            "/query",
            json={
                "session_id": "integration-session",
                "query": "What is NIRMIQ focused on?",
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )
        assert query_response.status_code == 200
        body = query_response.json()
        assert body["answer"].strip() != ""
        assert body["grounded"] is True
        assert len(body["citations"]) >= 1
        assert body["citations"][0]["excerpt"].strip() != ""
        assert isinstance(body["citations"][0]["score"], float)
        assert body["retrieval_meta"]["generation_backend"] in {"ollama", "fallback"}
        assert body["retrieval_meta"]["requested_retrieval_mode"] == "bm25"
        assert body["retrieval_meta"]["strategy"] == "phase1_bm25"
        assert body["retrieval_meta"]["max_chunks_per_document"] == 2
        assert body["retrieval_meta"]["grounding_state"] in {"strong", "moderate", "weak"}
        assert isinstance(body["retrieval_meta"]["grounding_summary"], str)
        assert body["retrieval_meta"]["citation_count"] >= 1

        timeline_response = client.get("/memory/integration-session/timeline")
        assert timeline_response.status_code == 200
        timeline_body = timeline_response.json()
        assert timeline_body["session_id"] == "integration-session"
        assert timeline_body["message_count"] >= 2
        assert len(timeline_body["messages"]) >= 2
        assert timeline_body["messages"][-1]["role"] == "assistant"
        assert timeline_body["messages"][-1]["retrieval_meta"]["requested_retrieval_mode"] == "bm25"
