import re

from app.domain.recursive_summary import (
    RECURSIVE_SUMMARY_VERSION,
    build_recursive_summary,
    render_recursive_summary,
)


def _row(
    index: int,
    *,
    heading: str,
    section_id: str,
    text: str | None = None,
) -> dict[str, object]:
    return {
        "id": f"chunk-{index}",
        "document_id": "doc-1",
        "chunk_index": index,
        "page_start": index + 1,
        "page_end": index + 1,
        "text": text
        or (
            f"{heading} explains the central idea for source region {index}. "
            "The method uses grounded observations and reports a practical result."
        ),
        "quality_score": 1.0,
        "section_id": section_id,
        "heading": heading,
        "section_path": heading,
        "chunk_type": "body",
    }


def test_recursive_summary_preserves_order_hierarchy_and_original_provenance() -> None:
    rows = [
        _row(3, heading="2.1 Evaluation", section_id="s-4"),
        _row(0, heading="Chapter 1 Foundations", section_id="s-1"),
        _row(2, heading="Chapter 2 Validation", section_id="s-3"),
        _row(1, heading="1.1 Signals", section_id="s-2"),
    ]

    summary = build_recursive_summary(rows)

    assert summary is not None
    assert summary.metadata["hierarchy_version"] == RECURSIVE_SUMMARY_VERSION
    assert summary.metadata["source_chunk_ids"] == [
        "chunk-0",
        "chunk-1",
        "chunk-2",
        "chunk-3",
    ]
    assert [node.label for node in summary.display_nodes] == [
        "Chapter 1 Foundations",
        "Chapter 2 Validation",
    ]
    assert summary.section_count == 4
    assert summary.chapter_count == 2

    answer, cited_rows = render_recursive_summary(summary)

    assert "### Chapter-by-chapter" in answer
    assert "#### Chapter 1 Foundations (pp. 1-2)" in answer
    assert "#### Chapter 2 Validation (pp. 3-4)" in answer
    assert cited_rows
    assert all(row in rows for row in cited_rows)
    anchors = [int(value) for value in re.findall(r"\[(\d+)\]", answer)]
    assert anchors
    assert max(anchors) == len(cited_rows)


def test_recursive_summary_retains_equation_table_and_diagram_evidence() -> None:
    rows = [
        _row(
            0,
            heading="Chapter 1 Control",
            section_id="s-1",
            text=(
                "The stability margin is calculated as M = (target - measured) / max(abs(target), epsilon). "
                "Low drift requires normal monitoring, while high drift requires immediate recalibration. "
                "Figure 1 shows the sensor, comparator, controller, and actuator feedback chain."
            ),
        )
    ]

    summary = build_recursive_summary(rows)

    assert summary is not None
    answer, cited_rows = render_recursive_summary(summary)
    assert "M = (target - measured)" in answer
    assert "immediate recalibration" in answer
    assert "Figure 1" in answer
    assert [row["id"] for row in cited_rows] == ["chunk-0"]


def test_recursive_summary_reduces_many_sections_without_dropping_coverage() -> None:
    rows = [
        _row(index, heading=f"Section {index + 1}", section_id=f"s-{index}")
        for index in range(25)
    ]

    summary = build_recursive_summary(rows, max_display_groups=4, reduction_fanout=3)

    assert summary is not None
    assert summary.metadata["source_chunks_considered"] == 25
    assert summary.section_count == 25
    assert len(summary.display_nodes) <= 4
    assert summary.reduction_depth >= 3
    assert len(summary.root.source_chunk_ids) == 25


def test_recursive_summary_is_deterministic() -> None:
    rows = [
        _row(index, heading=f"Chapter {index + 1} Topic", section_id=f"s-{index}")
        for index in range(8)
    ]

    first = build_recursive_summary(list(reversed(rows)), reduction_fanout=3)
    second = build_recursive_summary(rows, reduction_fanout=3)

    assert first is not None and second is not None
    assert first.metadata == second.metadata
    assert first.root.node_id == second.root.node_id
    assert render_recursive_summary(first) == render_recursive_summary(second)


def test_recursive_summary_does_not_repeat_section_heading_in_fact_text() -> None:
    rows = [
        _row(
            0,
            heading="Chapter 1 Foundations",
            section_id="s-1",
            text=(
                "Chapter 1 Foundations Adaptive sampling changes the measurement interval "
                "according to signal variation."
            ),
        )
    ]

    summary = build_recursive_summary(rows)

    assert summary is not None
    answer, _ = render_recursive_summary(summary)
    assert "- Adaptive sampling changes" in answer
    assert "- Chapter 1 Foundations Adaptive" not in answer


def test_recursive_summary_rejects_false_chapter_references_and_index_fragments() -> None:
    rows = [
        _row(
            0,
            heading="Chapter 1. Foundations",
            section_id="s-1",
            text="Chapter 1. Foundations Foundations define the core learning problem clearly.",
        ),
        _row(
            1,
            heading="Chapter 5. How does the best predictor perform?",
            section_id="s-2",
            text="This exercise refers to a later chapter but is not a chapter boundary.",
        ),
        _row(
            2,
            heading="Chapter 2. Validation",
            section_id="s-3",
            text="Chapter 2. Validation Validation compares behavior with a known target.",
        ),
        _row(
            3,
            heading="Accuracy Using Cross-Validation",
            section_id="s-4",
            text=(
                "Accuracy Using Cross-Validation, ACF, action advantage, reinforcement learning, "
                "credit assignment, activation functions, backpropagation, batch normalization, "
                "beam search, Bayesian models, classification, clustering"
            ),
        ),
    ]

    summary = build_recursive_summary(rows)

    assert summary is not None
    assert [node.label for node in summary.display_nodes] == [
        "Chapter 1. Foundations",
        "Chapter 2. Validation",
    ]
    answer, _ = render_recursive_summary(summary)
    assert "Accuracy Using Cross-Validation, ACF" not in answer


def test_recursive_summary_keeps_short_structural_headings_and_monotonic_gaps() -> None:
    rows = [
        _row(
            0,
            heading="Chapter 1. Foundations",
            section_id="s-1",
            text="Chapter 1. Foundations",
        ),
        _row(
            1,
            heading="Chapter 1. Foundations",
            section_id="s-1",
            text="Foundations explain the first principle using measured evidence.",
        ),
        _row(
            2,
            heading="Chapter 3. Validation",
            section_id="s-3",
            text="Chapter 3. Validation",
        ),
        _row(
            3,
            heading="Chapter 3. Validation",
            section_id="s-3",
            text="Validation compares measured behavior with a known target.",
        ),
        _row(
            4,
            heading="Appendix A. Equations",
            section_id="a-1",
            text="Appendix A. Equations",
        ),
        _row(
            5,
            heading="Appendix A. Equations",
            section_id="a-1",
            text="The appendix records the equations used by the method.",
        ),
    ]

    summary = build_recursive_summary(rows)

    assert summary is not None
    assert [node.label for node in summary.display_nodes] == [
        "Chapter 1. Foundations + Chapter 2 (heading unavailable)",
        "Chapter 3. Validation",
        "Appendix A. Equations",
    ]


def test_recursive_summary_repairs_common_pdf_mojibake_in_answer() -> None:
    rows = [
        _row(
            0,
            heading="Chapter 1. Training",
            section_id="s-1",
            text="Chapter 1. Training Letâs compare the modelâs output with the target.",
        )
    ]

    summary = build_recursive_summary(rows)

    assert summary is not None
    answer, _ = render_recursive_summary(summary)
    assert "Let's compare the model's output" in answer
    assert "â" not in answer


def test_recursive_summary_rejects_unreadable_rows() -> None:
    assert build_recursive_summary([{"id": "empty", "text": "too short"}]) is None
