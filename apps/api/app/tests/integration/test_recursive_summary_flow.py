from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_recursive_document_summary_and_scoped_cache_are_isolated(tmp_path: Path) -> None:
    source = tmp_path / "recursive-summary-source.txt"
    source.write_text(
        "\n".join(
            [
                "Chapter 1 Foundations",
                "Adaptive sampling changes the measurement interval according to signal variation. "
                "Stable signals are sampled less often, while rapid changes receive more observations.",
                "1.1 Signal Quality",
                "Signal quality depends on calibration and controlled measurement noise. "
                "The method begins by removing sensor bias before collecting reference readings.",
                "Chapter 2 Validation",
                "Validation compares measured behavior with a known target. "
                "The stability margin is calculated as M = (target - measured) / max(abs(target), epsilon).",
                "2.1 Limitations",
                "Although adaptive sampling reduces redundant measurements, it can miss events when the "
                "variation threshold is configured too high. A second observation reduces this risk.",
            ]
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        ingest = client.post(
            "/ingest",
            json={
                "source_path": str(source),
                "title": "Recursive Summary Fixture",
                "mime_type": "text/plain",
            },
        )
        assert ingest.status_code == 200
        document_id = ingest.json()["document_id"]

        request = {
            "session_id": "recursive-summary-session",
            "query": "Summarize this document",
            "document_id": document_id,
            "mode": "summary",
            "retrieval_mode": "bm25",
            "debug": True,
        }
        first = client.post("/query", json=request)
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["grounded"] is True
        assert "Chapter 1 Foundations" in first_body["answer"]
        assert "Chapter 2 Validation" in first_body["answer"]
        assert first_body["retrieval_meta"]["strategy"] == "recursive_document_summary"
        hierarchy = first_body["retrieval_meta"]["summary_hierarchy"]
        assert hierarchy["source_chunks_considered"] == 4
        assert hierarchy["sections_considered"] == 4
        assert hierarchy["chapter_groups"] == 2
        assert first_body["retrieval_meta"]["citation_coverage"] == 1.0
        assert first_body["retrieval_meta"]["citation_support"]["cache_safe"] is True
        assert first_body["citations"]

        cached = client.post("/query", json=request)
        assert cached.status_code == 200
        cached_body = cached.json()
        assert cached_body["answer"] == first_body["answer"]
        assert cached_body["retrieval_meta"]["cache_hit"] is True
        assert cached_body["retrieval_meta"]["cache_validation"]["cache_consistent"] is True

        scoped_request = {
            **request,
            "query": "Summarize chapter 2",
        }
        scoped = client.post("/query", json=scoped_request)
        assert scoped.status_code == 200
        scoped_body = scoped.json()
        assert scoped_body["retrieval_meta"]["cache_hit"] is False
        assert scoped_body["retrieval_meta"]["summary_profile"] != first_body["retrieval_meta"][
            "summary_profile"
        ]

        cached_scoped = client.post("/query", json=scoped_request)
        assert cached_scoped.status_code == 200
        assert cached_scoped.json()["answer"] == scoped_body["answer"]
        assert cached_scoped.json()["retrieval_meta"]["cache_hit"] is True
