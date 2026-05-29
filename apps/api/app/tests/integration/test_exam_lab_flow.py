from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_exam_lab_profile_question_bank_and_diagram_contracts(tmp_path: Path) -> None:
    sample = tmp_path / "exam_notes.txt"
    sample.write_text(
        "Retrieval augmented generation combines search with grounded answer synthesis.",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        ingest_response = client.post(
            "/ingest",
            json={"source_path": str(sample), "title": "Exam Notes", "mime_type": "text/plain"},
        )
        assert ingest_response.status_code == 200
        document_id = ingest_response.json()["document_id"]

        profile_response = client.post(
            "/exam/profiles",
            json={
                "session_id": "exam-session",
                "document_id": document_id,
                "title": "RAG Exam Profile",
                "marks": 10,
                "answer_style": "stepwise",
                "content_type": "conceptual",
                "instructions": "Use headings and cite source chunks.",
            },
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["document_id"] == document_id
        assert profile["marks"] == 10

        question_response = client.post(
            "/exam/question-bank/import",
            json={
                "document_id": document_id,
                "raw_text": "1. Explain retrieval augmented generation. (10 marks)\n2. What is grounded synthesis?",
            },
        )
        assert question_response.status_code == 200
        question_body = question_response.json()
        assert question_body["imported_count"] == 2
        assert question_body["items"][0]["marks"] == 10

        list_response = client.get(f"/exam/question-bank/{document_id}")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 2

        query_response = client.post(
            "/query",
            json={
                "session_id": "exam-session",
                "document_id": document_id,
                "query": "Generate a study guide from the imported question bank.",
                "mode": "study_guide",
                "retrieval_mode": "bm25",
                "retrieval_profile": "precision",
                "exam_profile": {
                    "marks": 10,
                    "answer_style": "stepwise",
                    "content_type": "conceptual",
                    "instructions": "Use headings and cite source chunks.",
                },
                "debug": True,
            },
        )
        assert query_response.status_code == 200
        query_body = query_response.json()
        assert query_body["grounded"] is True
        assert query_body["retrieval_meta"]["exam_profile_used"] is True
        assert query_body["retrieval_meta"]["exam_context_used"] is True
        assert query_body["retrieval_meta"]["exam_profile"]["marks"] == 10
        assert query_body["retrieval_meta"]["exam_context"]["question_count"] == 2
        assert query_body["retrieval_meta"]["exam_context"]["diagram_count"] == 0

        diagram_response = client.post(
            "/exam/diagrams/extract",
            json={"document_id": document_id, "force": True},
        )
        assert diagram_response.status_code == 200
        assert diagram_response.json()["extracted_count"] == 0

        missing_asset_response = client.get("/exam/diagrams/assets/missing-asset")
        assert missing_asset_response.status_code == 404
