from app.domain.summary_reliability import (
    audit_citation_support,
    measure_summary_runtime,
    validate_persisted_summary_meta,
    validate_cached_summary,
)


def test_citation_support_accepts_matching_excerpt_and_rejects_wrong_excerpt() -> None:
    answer = "Adaptive sampling changes the measurement interval when signal variation changes. [1]"
    matching = [{"id": "chunk-1", "excerpt": "Adaptive sampling changes the measurement interval according to signal variation."}]
    wrong = [{"id": "chunk-2", "excerpt": "The appendix lists unrelated validation references and page numbers."}]

    assert audit_citation_support(answer, matching)["cache_safe"] is True
    wrong_audit = audit_citation_support(answer, wrong)
    assert wrong_audit["cache_safe"] is False
    assert wrong_audit["unsupported_citation_count"] == 1


def test_citation_support_respects_sparse_explicit_anchor_numbers() -> None:
    result = audit_citation_support(
        "The source defines a measured target. [10]",
        [
            {
                "anchor": 10,
                "id": "chunk-10",
                "text": "The source defines a measured target.",
            }
        ],
    )

    assert result["cache_safe"] is True
    assert result["invalid_anchor_count"] == 0


def test_cached_summary_validation_requires_current_hierarchy_and_supported_citations() -> None:
    answer = "The stability margin is calculated from the target and measured values. [1]"
    citations = [{"chunk_id": "chunk-1", "excerpt": "The stability margin is calculated from the target and measured values."}]
    meta = {
        "summary_profile": "bm25:balanced:recursive-extractive-v6:document",
        "summary_hierarchy": {"hierarchy_version": "recursive-extractive-v6"},
    }

    result = validate_cached_summary(answer, citations, meta)

    assert result["cache_consistent"] is True
    assert result["issues"] == []


def test_cached_summary_validation_rejects_stale_hierarchy() -> None:
    result = validate_cached_summary(
        "The source defines a measured target. [1]",
        [{"chunk_id": "chunk-1", "excerpt": "The source defines a measured target."}],
        {
            "summary_profile": "bm25:balanced:recursive-extractive-v5:document",
            "strategy": "recursive_document_summary",
            "summary_hierarchy": {"hierarchy_version": "recursive-extractive-v5"},
        },
    )

    assert result["cache_consistent"] is False
    assert "summary_version_missing_or_stale" in result["issues"]


def test_cached_summary_validation_rejects_reindexed_chunk_ids() -> None:
    result = validate_cached_summary(
        "The source defines a measured target. [1]",
        [{"chunk_id": "old-chunk", "excerpt": "The source defines a measured target."}],
        {
            "summary_profile": "bm25:balanced:recursive-extractive-v6:document",
            "summary_hierarchy": {
                "hierarchy_version": "recursive-extractive-v6",
                "source_chunk_ids": ["old-chunk"],
            },
        },
        active_rows=[
            {"id": "new-chunk", "text": "The source defines a measured target."}
        ],
    )

    assert result["cache_consistent"] is False
    assert "citation_chunk_not_in_active_index" in result["issues"]
    assert "summary_source_not_in_active_index" in result["issues"]


def test_persisted_summary_metadata_requires_provenance_fields() -> None:
    result = validate_persisted_summary_meta({})

    assert result["valid"] is False
    assert "summary_profile_missing_or_invalid" in result["issues"]
    assert "summary_hierarchy_missing_or_invalid" in result["issues"]


def test_cached_summary_validation_rejects_active_but_out_of_scope_citation() -> None:
    result = validate_cached_summary(
        "The source defines a measured target. [1]",
        [
            {
                "document_id": "other-document",
                "chunk_id": "other-chunk",
                "excerpt": "The source defines a measured target.",
            }
        ],
        {
            "summary_profile": "bm25:balanced:recursive-extractive-v6:document",
            "strategy": "recursive_document_summary",
            "response_mode": "summary",
            "summary_hierarchy": {
                "hierarchy_version": "recursive-extractive-v6",
                "source_chunk_ids": ["other-chunk"],
            },
        },
        active_rows=[
            {
                "id": "other-chunk",
                "document_id": "other-document",
                "text": "The source defines a measured target.",
            }
        ],
        document_id="selected-document",
    )

    assert result["cache_consistent"] is False
    assert "citation_document_scope_mismatch" in result["issues"]
    assert "active_rows_scope_mismatch" in result["issues"]


def test_summary_runtime_measurement_is_bounded_and_reports_memory() -> None:
    rows = [
        {
            "id": f"chunk-{index}",
            "document_id": "doc-1",
            "chunk_index": index,
            "page_start": index + 1,
            "page_end": index + 1,
            "section_id": f"section-{index}",
            "heading": f"Chapter {index + 1}. Topic",
            "section_path": f"Chapter {index + 1}. Topic",
            "text": f"Chapter {index + 1}. Topic explains a measured method and its practical limitation for source region {index}.",
        }
        for index in range(8)
    ]

    result = measure_summary_runtime(rows, repeats=2)

    assert result["runs"] == 2
    assert result["source_rows"] == 8
    assert result["first_ms"] >= 0
    assert result["peak_allocated_kib"] > 0
