from app.domain.hierarchical_summary import (
    HIERARCHICAL_SUMMARY_VERSION,
    select_hierarchical_summary_seeds,
)
from app.services.query_service import QueryService


def _row(index: int, section: str | None) -> dict[str, object]:
    return {
        "id": f"chunk-{index}",
        "document_id": "doc-1",
        "text": (
            f"This section explains the main method and evidence for region {index}. "
            "It includes enough original source language to remain a readable summary seed. "
            "The discussion also records a result and its practical limitation."
        ),
        "page_start": index + 1,
        "page_end": index + 1,
        "quality_score": 1.0,
        "section_id": f"section-{section}" if section else None,
        "heading": section,
        "section_path": section,
        "chunk_type": "body",
    }


def test_hierarchical_summary_selects_original_chunks_across_sections() -> None:
    rows = [
        _row(index, section)
        for index, section in enumerate(
            ["Introduction"] * 3
            + ["Methods"] * 3
            + ["Results"] * 3
            + ["Limitations"] * 3
        )
    ]

    seeds, meta = select_hierarchical_summary_seeds(rows, max_seeds=4)

    assert [seed.coverage_key for seed in seeds] == [
        "Introduction",
        "Methods",
        "Results",
        "Limitations",
    ]
    assert all(seed.row in rows for seed in seeds)
    assert meta["provenance"] == "original_document_chunks"
    assert meta["hierarchy_version"] == HIERARCHICAL_SUMMARY_VERSION


def test_hierarchical_summary_falls_back_to_document_regions_deterministically() -> None:
    rows = [_row(index, None) for index in range(16)]

    first, first_meta = select_hierarchical_summary_seeds(rows, max_seeds=4)
    second, second_meta = select_hierarchical_summary_seeds(rows, max_seeds=4)

    assert [seed.row["id"] for seed in first] == [seed.row["id"] for seed in second]
    assert len(first) == 4
    assert first_meta == second_meta
    assert first_meta["selected_groups"] == [
        "document-region-1",
        "document-region-2",
        "document-region-3",
        "document-region-4",
    ]


def test_summary_cache_profile_invalidates_pre_recursive_answers() -> None:
    profile = QueryService._summary_profile(
        retrieval_mode="bm25",
        retrieval_profile="balanced",
        query="Summarize this document",
    )

    assert profile == "bm25:balanced:recursive-extractive-v6:document"


def test_summary_cache_profile_separates_scoped_questions() -> None:
    methods = QueryService._summary_profile(
        retrieval_mode="bm25",
        retrieval_profile="balanced",
        query="Summarize the methods",
    )
    limitations = QueryService._summary_profile(
        retrieval_mode="bm25",
        retrieval_profile="balanced",
        query="Summarize the limitations",
    )

    assert methods != limitations
    assert methods.startswith("bm25:balanced:recursive-extractive-v6:")


def test_document_wide_summary_detection_keeps_scoped_requests_on_rag_path() -> None:
    assert QueryService._is_document_wide_summary_query("Summarize this PDF") is True
    assert QueryService._is_document_wide_summary_query("Explain the document") is True
    assert QueryService._is_document_wide_summary_query("Summarize chapter 4") is False
    assert QueryService._is_document_wide_summary_query("Summarize the methodology") is False
