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
    assert artifact["source_diversity"]["unique_documents"] == 2
    assert artifact["source_diversity"]["status"] == "balanced"
    assert "related_work" in artifact["section_templates"]
    assert any("citations" in guardrail for guardrail in artifact["guardrails"])


def test_paper_lab_artifact_keeps_source_diversity_when_possible() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id=f"a-{index}",
            document_id="doc-a",
            text=f"Background evidence item {index} explains the academic system design.",
            score=1.0 - (index * 0.01),
            page_start=index,
            source="bm25",
            quality_score=0.9,
        )
        for index in range(1, 8)
    ]
    chunks.extend(
        [
            RetrievedChunk(
                chunk_id="b-1",
                document_id="doc-b",
                text="A second paper gives related work evidence for comparison.",
                score=0.62,
                page_start=12,
                source="bm25",
                quality_score=0.88,
            ),
            RetrievedChunk(
                chunk_id="c-1",
                document_id="doc-c",
                text="A third source discusses limitations and future work caveats.",
                score=0.58,
                page_start=15,
                source="bm25",
                quality_score=0.84,
            ),
        ]
    )

    artifact = build_paper_lab_artifact(chunks)

    matrix_document_ids = {
        cluster_item["document_id"]
        for cluster_items in artifact["citation_clusters"].values()
        for cluster_item in cluster_items
    }
    assert {"doc-a", "doc-b", "doc-c"}.issubset(matrix_document_ids)
    assert artifact["source_diversity"]["unique_documents"] == 3
    assert artifact["source_diversity"]["dominant_document_share"] <= 0.5


def test_paper_lab_artifact_warns_for_single_source_evidence() -> None:
    artifact = build_paper_lab_artifact(
        [
            RetrievedChunk(
                chunk_id="only-1",
                document_id="doc-only",
                text="The only available source supports a narrow grounded draft.",
                score=0.7,
                page_start=1,
                source="bm25",
                quality_score=0.8,
            )
        ]
    )

    assert artifact["source_diversity"]["status"] == "single_source"
    assert any("one source" in guardrail for guardrail in artifact["guardrails"])
