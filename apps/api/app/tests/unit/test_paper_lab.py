from app.domain.models import RetrievedChunk
from app.domain.paper_lab import build_paper_lab_artifact


def test_paper_lab_artifact_builds_matrix_and_clusters() -> None:
    artifact = build_paper_lab_artifact(
        [
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="The system architecture uses retrieval and grounded synthesis for academic workflows.",
                score=0.9,
                page_start=2,
                page_end=2,
                source="bm25",
                quality_score=0.95,
            ),
            RetrievedChunk(
                chunk_id="chunk-2",
                document_id="doc-2",
                text="The evaluation results show improved citation coverage and answer faithfulness.",
                score=0.8,
                page_start=5,
                page_end=5,
                source="hybrid",
                quality_score=0.9,
            ),
        ]
    )

    assert artifact["source_count"] == 2
    assert artifact["evidence_count"] == 2
    assert len(artifact["related_work_matrix"]) == 2
    assert "methodology" in artifact["citation_clusters"]
    assert "results" in artifact["citation_clusters"]
    assert artifact["outline"][0] == "Title and problem framing"
