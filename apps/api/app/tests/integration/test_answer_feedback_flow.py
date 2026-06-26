from fastapi.testclient import TestClient

from app.main import app


def test_answer_feedback_api_contract_and_clear_session() -> None:
    with TestClient(app) as client:
        feedback_response = client.post(
            "/memory/review-session/feedback",
            json={
                "rating": "needs_work",
                "query": "Explain PCA from the selected textbook.",
                "answer": "PCA reduces dimensionality.",
                "source_title": "Machine Learning Notes",
                "reason": "needs_more_citations",
            },
        )
        assert feedback_response.status_code == 200
        feedback = feedback_response.json()
        assert feedback["session_id"] == "review-session"
        assert feedback["rating"] == "needs_work"
        assert feedback["query"].startswith("Explain PCA")
        assert feedback["created_at"]

        list_response = client.get("/memory/review-session/feedback")
        assert list_response.status_code == 200
        body = list_response.json()
        assert body["session_id"] == "review-session"
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == feedback["id"]

        clear_response = client.delete("/memory/review-session")
        assert clear_response.status_code == 200
        assert clear_response.json()["deleted"] is True

        cleared_list_response = client.get("/memory/review-session/feedback")
        assert cleared_list_response.status_code == 200
        assert cleared_list_response.json()["items"] == []
