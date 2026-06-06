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
