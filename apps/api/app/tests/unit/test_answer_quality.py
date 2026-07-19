from app.domain.answer_quality import evaluate_answer_quality


def _supported_meta() -> dict[str, object]:
    return {
        "citation_coverage": 1.0,
        "citation_verification_state": "supported",
        "unsupported_claims": [],
    }


def test_query_specific_supported_answer_passes_quality_gate() -> None:
    result = evaluate_answer_quality(
        query="How does scaled dot-product attention work?",
        answer=(
            "Attention computes dot products between each query and the keys, scales the scores, "
            "applies softmax, and uses the weights to combine the values. [1]"
        ),
        grounded=True,
        retrieval_meta=_supported_meta(),
        expected_answer="It computes query-key dot products, applies scaling and softmax, then combines values.",
        required_concepts=[
            ["dot products", "dot product"],
            ["query", "queries"],
            ["keys", "key"],
            ["softmax"],
            ["values", "value"],
        ],
    )

    assert result["passed"] is True
    assert result["concept_coverage"] == 1.0
    assert result["faithfulness"] == 1.0


def test_related_but_nonanswering_text_fails_answer_relevance() -> None:
    result = evaluate_answer_quality(
        query="Explain CNN",
        answer="CNN architectures include semantic segmentation and object detection tasks. [1]",
        grounded=True,
        retrieval_meta=_supported_meta(),
        required_concepts=[
            ["convolutional layers"],
            ["filters", "kernels"],
            ["pooling layers", "pooling"],
        ],
    )

    assert result["passed"] is False
    assert "low_answer_relevance" in result["failure_reasons"]


def test_unanswerable_query_passes_only_with_clear_abstention() -> None:
    result = evaluate_answer_quality(
        query="Explain the Zeloria treaty.",
        answer="This topic was not found in the selected source, so I need more context.",
        grounded=False,
        retrieval_meta={},
        answerability="unanswerable",
    )

    assert result["passed"] is True
    assert result["answerability_correct"] == 1.0


def test_confident_unanswerable_response_fails_answerability() -> None:
    result = evaluate_answer_quality(
        query="Explain the Zeloria treaty.",
        answer="The Zeloria treaty regulates orbital cuisine. [1]",
        grounded=True,
        retrieval_meta=_supported_meta(),
        answerability="unanswerable",
    )

    assert result["passed"] is False
    assert "answerability_mismatch" in result["failure_reasons"]


def test_current_not_enough_direct_evidence_wording_counts_as_abstention() -> None:
    result = evaluate_answer_quality(
        query="What is not covered here?",
        answer="I found a related mention, but not enough direct evidence to answer confidently.",
        grounded=False,
        retrieval_meta={},
        answerability="unanswerable",
    )

    assert result["answerability_correct"] == 1.0
    assert result["passed"] is True


def test_runtime_not_found_wording_counts_as_abstention() -> None:
    result = evaluate_answer_quality(
        query="What launch date is stated?",
        answer="I could not find this in the uploaded sources.",
        grounded=False,
        retrieval_meta={},
        answerability="unanswerable",
    )

    assert result["answerability_correct"] == 1.0
    assert result["passed"] is True


def test_symbolic_formula_satisfies_requested_equation_plan() -> None:
    result = evaluate_answer_quality(
        query="How is the stability margin calculated?",
        answer=(
            "The stability margin is calculated as "
            "M = (target - measured) / max(abs(target), epsilon). [1]"
        ),
        grounded=True,
        retrieval_meta=_supported_meta(),
        required_concepts=[
            ["target - measured"],
            ["max(abs(target), epsilon)"],
        ],
    )

    assert result["plan_checks"]["requested_equations"] is True
    assert result["passed"] is True


def test_orphan_fragment_reduces_readability_score() -> None:
    result = evaluate_answer_quality(
        query="Compare random forests and decision trees.",
        answer=(
            "Random forests aggregate multiple decision trees, while one decision tree uses a single model. [1]\n"
            "- Validation error remains lower vs"
        ),
        grounded=True,
        retrieval_meta=_supported_meta(),
        required_concepts=[["multiple decision trees"], ["single model"]],
    )

    assert result["readability"] < 1.0
    assert result["readability_issues"]
