from app.domain.citation_coverage import citation_coverage


def test_citation_coverage_scores_cited_claims() -> None:
    result = citation_coverage(
        "Attention uses query, key, and value projections. [1] "
        "The model also uses positional encodings. [2]"
    )

    assert result["citation_coverage"] == 1.0
    assert result["citation_sentence_count"] == 2
    assert result["citation_anchor_count"] == 2


def test_citation_coverage_flags_low_coverage() -> None:
    result = citation_coverage(
        "Attention uses query, key, and value projections. [1] "
        "The model is always better for every task."
    )

    assert result["citation_coverage"] == 0.5
    assert result["citation_sentence_count"] == 2
    assert result["citation_anchor_count"] == 1


def test_citation_coverage_ignores_markdown_headings() -> None:
    result = citation_coverage(
        "## Document summary\n\n"
        "### Chapter-by-chapter\n\n"
        "#### Chapter 1 Foundations (pp. 1-3)\n"
        "- Adaptive sampling changes its interval with signal variation. [1]\n\n"
        "#### Chapter 2 Validation (pp. 4-6)\n"
        "- Validation compares measured behavior with a known target. [2]"
    )

    assert result["citation_coverage"] == 1.0
    assert result["citation_sentence_count"] == 2
    assert result["citation_anchor_count"] == 2
