import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_retrieval_modes_available_after_ingest(tmp_path: Path) -> None:
    sample = tmp_path / "modes_sample.txt"
    sample.write_text(
        "NIRMIQ uses lexical and semantic retrieval with reciprocal rank fusion.",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        ingest_response = client.post(
            "/ingest",
            json={"source_path": str(sample), "title": "Modes", "mime_type": "text/plain"},
        )
        assert ingest_response.status_code == 200

        container = app.state.container
        hybrid = asyncio.run(
            container.retrieval_service.retrieve_with_mode(
                "What retrieval strategy does NIRMIQ use?", mode="hybrid"
            )
        )
        bm25 = asyncio.run(
            container.retrieval_service.retrieve_with_mode(
                "What retrieval strategy does NIRMIQ use?", mode="bm25"
            )
        )
        vector = asyncio.run(
            container.retrieval_service.retrieve_with_mode(
                "What retrieval strategy does NIRMIQ use?", mode="vector"
            )
        )

        assert hybrid.meta["strategy"] == "nirmiq_ehr_hybrid"
        assert bm25.meta["strategy"] == "nirmiq_ehr_bm25"
        assert vector.meta["strategy"] == "nirmiq_ehr_vector"
        assert hybrid.meta["retrieval_method"] == "nirmiq_evidence_first_hierarchical_hybrid_rag"


def test_query_can_scope_retrieval_to_selected_document(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    first.write_text(
        "NIRMIQ is a local research assistant for retrieval workflows.",
        encoding="utf-8",
    )
    second = tmp_path / "second.txt"
    second.write_text(
        "Stoicism is a practical philosophy about attention, discipline, and wise action.",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        first_response = client.post(
            "/ingest",
            json={"source_path": str(first), "title": "NIRMIQ", "mime_type": "text/plain"},
        )
        second_response = client.post(
            "/ingest",
            json={"source_path": str(second), "title": "Stoicism", "mime_type": "text/plain"},
        )
        assert first_response.status_code == 200
        assert second_response.status_code == 200
        selected_document_id = second_response.json()["document_id"]

        query_response = client.post(
            "/query",
            json={
                "session_id": "scoped-session",
                "query": "What is Stoicism about?",
                "document_id": selected_document_id,
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )

        assert query_response.status_code == 200
        body = query_response.json()
        assert body["retrieval_meta"]["scope"] == "document"
        assert body["retrieval_meta"]["document_scope"] == selected_document_id
        assert body["citations"]
        assert {citation["document_id"] for citation in body["citations"]} == {selected_document_id}


def test_selected_document_query_includes_section_first_diagnostics(tmp_path: Path) -> None:
    sample = tmp_path / "sectioned_textbook.txt"
    sample.write_text(
        "\n".join(
            [
                "Chapter 1 Retrieval Systems",
                "NIRMIQ uses citation grounded retrieval with BM25 and reciprocal rank fusion.",
                "Evidence chunks are selected to answer questions from the source material.",
                "Chapter 2 Interface Design",
                "The interface keeps controls compact so students can read answers clearly.",
            ]
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        ingest_response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Sectioned Textbook",
                "mime_type": "text/plain",
            },
        )
        assert ingest_response.status_code == 200
        document_id = ingest_response.json()["document_id"]

        query_response = client.post(
            "/query",
            json={
                "session_id": "section-diagnostics-session",
                "query": "What does NIRMIQ use for grounded retrieval?",
                "document_id": document_id,
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )

        assert query_response.status_code == 200
        meta = query_response.json()["retrieval_meta"]
        assert meta["section_first_enabled"] is True
        assert meta["section_candidates"]
        assert meta["chunk_selection_reasons"]
        assert meta["retrieval_diagnostics"]["returned_chunks"] >= 1
        assert any(reason["section_match"] for reason in meta["chunk_selection_reasons"])


def test_selected_document_comparison_recovers_obligation_candidates(tmp_path: Path) -> None:
    sample = tmp_path / "comparison_methods.txt"
    sample.write_text(
        (
            "Alpha method processes data in batches and waits for a complete input set. "
            "Beta method processes data continuously as each new item arrives."
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        ingest_response = client.post(
            "/ingest",
            json={
                "source_path": str(sample),
                "title": "Comparison Methods",
                "mime_type": "text/plain",
            },
        )
        assert ingest_response.status_code == 200
        document_id = ingest_response.json()["document_id"]

        query_response = client.post(
            "/query",
            json={
                "session_id": "comparison-obligation-session",
                "query": "Compare alpha method and beta method.",
                "document_id": document_id,
                "retrieval_mode": "bm25",
                "debug": True,
            },
        )

        assert query_response.status_code == 200
        body = query_response.json()
        assert body["grounded"] is True
        assert body["citations"]
        assert body["retrieval_meta"]["answer_plan_type"] == "comparison"
