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

        unrelated_response = client.post(
            "/query",
            json={
                "session_id": "integration-session",
                "query": "What does the corpus say about the Zeloria orbital cuisine treaty?",
                "mode": "general_chat",
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )
        assert unrelated_response.status_code == 200
        unrelated_body = unrelated_response.json()
        assert unrelated_body["grounded"] is False
        assert unrelated_body["citations"] == []
        assert "not have enough relevant uploaded context" in unrelated_body["answer"]
        assert unrelated_body["retrieval_meta"]["context_relevance_state"] == "unrelated"
        assert unrelated_body["retrieval_meta"]["grounding_state"] == "weak"

        summary_response = client.post(
            "/query",
            json={
                "session_id": "integration-session",
                "query": "Explain the document",
                "document_id": document_id,
                "mode": "summary",
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )
        assert summary_response.status_code == 200
        summary_body = summary_response.json()
        assert summary_body["grounded"] is True
        assert "Please ingest documents first" not in summary_body["answer"]
        assert "summary" in summary_body["answer"].lower()
        assert len(summary_body["citations"]) >= 1
        assert summary_body["retrieval_meta"]["document_overview_request"] is True
        assert summary_body["retrieval_meta"]["cache_hit"] is False
        assert summary_body["retrieval_meta"]["detected_intent"] == "summary"
        assert summary_body["retrieval_meta"]["citation_coverage"] >= 0
        assert summary_body["retrieval_meta"]["citation_sentence_count"] >= 1
        assert summary_body["retrieval_meta"]["citation_anchor_count"] >= 1

        cached_summary_response = client.post(
            "/query",
            json={
                "session_id": "integration-session",
                "query": "Explain the document",
                "document_id": document_id,
                "mode": "summary",
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )
        assert cached_summary_response.status_code == 200
        cached_summary_body = cached_summary_response.json()
        assert cached_summary_body["answer"] == summary_body["answer"]
        assert cached_summary_body["retrieval_meta"]["cache_hit"] is True
        assert cached_summary_body["retrieval_meta"]["intent_route"] == "summary_cache_hit"

        sample.write_text(
            (
                "NIRMIQ now focuses on cached document summaries. "
                "It still uses local retrieval and grounded synthesis with citations."
            ),
            encoding="utf-8",
        )
        reingest_response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Sample",
                "mime_type": "text/plain",
                "force_reindex": True,
            },
        )
        assert reingest_response.status_code == 200
        assert reingest_response.json()["document_id"] == document_id

        refreshed_summary_response = client.post(
            "/query",
            json={
                "session_id": "integration-session",
                "query": "Explain the document",
                "document_id": document_id,
                "mode": "summary",
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )
        assert refreshed_summary_response.status_code == 200
        refreshed_summary_body = refreshed_summary_response.json()
        assert refreshed_summary_body["retrieval_meta"]["cache_hit"] is False

        paper_response = client.post(
            "/query",
            json={
                "session_id": "integration-session",
                "query": "Draft a related work section from this document.",
                "document_id": document_id,
                "mode": "research_paper",
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )
        assert paper_response.status_code == 200
        paper_body = paper_response.json()
        assert paper_body["retrieval_meta"]["detected_intent"] == "paper_draft"
        assert paper_body["retrieval_meta"]["effective_retrieval_profile"] == "precision"
        assert paper_body["retrieval_meta"]["paper_lab"]["evidence_count"] >= 1
        assert paper_body["retrieval_meta"]["paper_lab"]["related_work_matrix"]

        timeline_response = client.get("/memory/integration-session/timeline")
        assert timeline_response.status_code == 200
        timeline_body = timeline_response.json()
        assert timeline_body["session_id"] == "integration-session"
        assert timeline_body["message_count"] >= 2
        assert len(timeline_body["messages"]) >= 2
        assert timeline_body["messages"][-1]["role"] == "assistant"
        assert timeline_body["messages"][-1]["retrieval_meta"]["requested_retrieval_mode"] == "bm25"

        delete_response = client.delete(f"/documents/{document_id}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {"document_id": document_id, "deleted": True}
        assert app.state.container.sqlite_repo.get_document_summary_count(document_id) == 0

        missing_detail = client.get(f"/documents/{document_id}")
        assert missing_detail.status_code == 404


def test_upload_ingest_roundtrip() -> None:
    with TestClient(app) as client:
        upload_response = client.post(
            "/ingest/upload",
            data={"title": "Uploaded Notes", "force_reindex": "true"},
            files={
                "file": (
                    "uploaded-notes.txt",
                    b"Uploaded files should enter the same grounded retrieval pipeline.",
                    "text/plain",
                )
            },
        )

        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]

        detail_response = client.get(f"/documents/{document_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["title"] == "Uploaded Notes"
        assert detail["active_chunk_count"] >= 1
        assert "uploaded-notes" in detail["source_path"]
