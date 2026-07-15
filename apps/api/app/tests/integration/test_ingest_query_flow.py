import os
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
        assert body["retrieval_meta"]["strategy"] == "nirmiq_ehr_bm25"
        assert body["retrieval_meta"]["retrieval_method"] == "nirmiq_evidence_first_hierarchical_hybrid_rag"
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
        assert "could not find this in the uploaded sources" in unrelated_body["answer"]
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
        assert paper_body["retrieval_meta"]["paper_lab"]["source_diversity"]["unique_documents"] >= 1
        assert paper_body["retrieval_meta"]["paper_lab"]["guardrails"]
        assert "related_work" in paper_body["retrieval_meta"]["paper_lab"]["section_templates"]

        timeline_response = client.get("/memory/integration-session/timeline")
        assert timeline_response.status_code == 200
        timeline_body = timeline_response.json()
        assert timeline_body["session_id"] == "integration-session"
        assert timeline_body["message_count"] >= 2
        assert len(timeline_body["messages"]) >= 2
        assert timeline_body["messages"][-1]["role"] == "assistant"
        assert timeline_body["messages"][-1]["retrieval_meta"]["requested_retrieval_mode"] == "bm25"

        export_response = client.get("/memory/integration-session/export")
        assert export_response.status_code == 200
        assert "NIRMIQ Thread Export" in export_response.text
        assert "What is NIRMIQ focused on?" in export_response.text
        assert "Citations:" in export_response.text

        clear_session_response = client.delete("/memory/integration-session")
        assert clear_session_response.status_code == 200
        clear_session_body = clear_session_response.json()
        assert clear_session_body["deleted"] is True
        assert clear_session_body["deleted_messages"] >= 2

        cleared_timeline_response = client.get("/memory/integration-session/timeline")
        assert cleared_timeline_response.status_code == 200
        assert cleared_timeline_response.json()["message_count"] == 0

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
        uploaded_source = Path(detail["source_path"])
        assert uploaded_source.exists()

        document_row = app.state.container.sqlite_repo.get_document_by_id(document_id)
        assert document_row is not None
        cache_root = Path(os.environ["PARSE_CACHE_PATH"])
        cache_file = cache_root / f"{document_row['content_hash']}.v1.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text('{"version": 1, "pages": []}', encoding="utf-8")
        assert cache_file.exists()

        upload_root = Path(os.environ["UPLOAD_PATH"])
        orphan_upload = upload_root / "orphan-upload.txt"
        orphan_upload.write_text("orphaned app upload", encoding="utf-8")
        orphan_cache = cache_root / "orphan-cache.json"
        orphan_cache.write_text("{}", encoding="utf-8")
        diagram_root = Path(os.environ["DIAGRAM_PATH"])
        orphan_diagram = diagram_root / "orphan-document" / "figure.png"
        orphan_diagram.parent.mkdir(parents=True, exist_ok=True)
        orphan_diagram.write_bytes(b"local-test-image")
        external_original = cache_root.parent / "external-original.txt"
        external_original.write_text("must remain outside app-owned roots", encoding="utf-8")

        purge_response = client.delete("/documents")
        assert purge_response.status_code == 200
        purge_body = purge_response.json()
        assert purge_body["deleted_count"] >= 1
        assert document_id in purge_body["deleted_document_ids"]
        assert purge_body["source_files_deleted"] is True
        assert purge_body["source_file_delete_count"] >= 2
        assert purge_body["derived_files_deleted"] >= 3
        assert not uploaded_source.exists()
        assert not cache_file.exists()
        assert not orphan_upload.exists()
        assert not orphan_cache.exists()
        assert not orphan_diagram.exists()
        assert external_original.exists()

        missing_detail = client.get(f"/documents/{document_id}")
        assert missing_detail.status_code == 404


def test_unreadable_reindex_preserves_existing_chunks(tmp_path: Path) -> None:
    sample = tmp_path / "reindex-source.txt"
    sample.write_text(
        "NIRMIQ should preserve existing active chunks when a later reindex extracts no readable text.",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        first_response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Reindex Source",
                "mime_type": "text/plain",
            },
        )
        assert first_response.status_code == 200
        document_id = first_response.json()["document_id"]
        first_detail = client.get(f"/documents/{document_id}").json()
        assert first_detail["active_chunk_count"] >= 1

        sample.write_text("    \n\t   ", encoding="utf-8")
        failed_reindex = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Reindex Source",
                "mime_type": "text/plain",
                "force_reindex": True,
            },
        )

        assert failed_reindex.status_code == 400
        detail_after_failure = client.get(f"/documents/{document_id}")
        assert detail_after_failure.status_code == 200
        body = detail_after_failure.json()
        assert body["status"] == "failed"
        assert body["active_chunk_count"] == first_detail["active_chunk_count"]


def test_direct_ingest_rejects_unsupported_local_file(tmp_path: Path) -> None:
    sample = tmp_path / "not-a-document.exe"
    sample.write_bytes(b"MZfake executable bytes")

    with TestClient(app) as client:
        response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Bad File",
                "mime_type": "application/octet-stream",
            },
        )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
