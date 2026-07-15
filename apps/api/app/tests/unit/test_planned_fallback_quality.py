from app.domain.answer_intelligence import build_answer_plan
from app.services.synthesis_service import SynthesisService


def test_mechanism_fallback_prefers_process_over_related_description() -> None:
    query = "How does gradient descent update model parameters?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Gradient descent is a common optimization algorithm used in machine learning.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "Gradient descent computes the gradient of the cost function for the model parameters. "
                "It then updates the parameters in the opposite direction to reduce the cost.",
            ),
        ],
    )

    assert "computes the gradient" in answer
    assert "updates the parameters" in answer
    assert "How it works" in answer
    assert "[2]" in answer


def test_comparison_fallback_selects_explicit_contrast() -> None:
    query = "Compare precision and recall"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=3-3\n"
                "Precision measures the fraction of positive predictions that are correct, whereas "
                "recall measures the fraction of actual positives that the model identifies.",
            )
        ],
    )

    assert "whereas recall" in answer
    assert "[1]" in answer


def test_limitation_fallback_does_not_return_only_a_definition() -> None:
    query = "What are the limitations of batch normalization?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=4-4\n"
                "Batch normalization normalizes each input feature. However, it adds computational "
                "overhead and can make each training step slower.",
            )
        ],
    )

    assert "computational overhead" in answer
    assert "slower" in answer
    assert "[1]" in answer


def test_factual_fallback_prefers_sentence_containing_release_date() -> None:
    query = "When was the third edition released?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Hands-On Machine Learning, Third Edition. The third edition was published in 2022.",
            )
        ],
    )

    assert "published in 2022" in answer
    assert "[1]" in answer


def test_mechanism_fallback_rejects_subject_mentioned_only_in_roadmap() -> None:
    query = "How does dropout regularize a neural network?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "In this section we will examine L1 regularization, L2 regularization, dropout, and max-norm. "
                "L1 regularization adds a penalty based on the absolute value of each weight.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "Dropout is a regularization technique. During training, it randomly drops some inputs "
                "by setting them to zero, which prevents neurons from relying on one another too much.",
            ),
        ],
    )

    assert "randomly drops" in answer
    assert "L1 regularization adds" not in answer
    assert "[2]" in answer


def test_mechanism_fallback_keeps_local_process_sentences() -> None:
    query = "How does DBSCAN identify clusters and anomalies?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=3-3\n"
                "DBSCAN defines clusters as continuous regions of high density. "
                "For each instance, it counts the neighboring instances within a small distance. "
                "Instances with enough neighbors are considered core instances. "
                "An instance that is not a core instance and has no core neighbor is identified as an anomaly.",
            ),
            (
                2,
                "[2] doc=doc score=.8 source=bm25 pages=4-4\n"
                "Gaussian mixture models represent clusters using Gaussian distributions.",
            ),
        ],
    )

    assert "counts the neighboring instances" in answer
    assert "identified as an anomaly" in answer
    assert "Gaussian mixture" not in answer


def test_factual_claim_verification_keeps_exact_edition_and_release_date() -> None:
    context = [
        (
            1,
            "[1] doc=doc score=1 source=bm25 pages=1-1\n"
            "Hands-On Machine Learning THIRD EDITION. 2022-10-03: First Release.",
        )
    ]
    answer = SynthesisService._fallback_factual_answer(
        query="Which edition and release date are shown?",
        context_chunks=context,
    )

    assert answer is not None
    assert SynthesisService._verify_cited_claims(answer, context)["state"] == "supported"


def test_mechanism_fallback_prefers_requested_focus_without_repeating_model_name() -> None:
    query = "How does the Transformer represent token positions?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=5-5\n"
                "The Transformer maps input tokens through learned embeddings before the softmax layer.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=6-6\n"
                "Since the model contains no recurrence, positional encodings are added to token "
                "embeddings so their positions in the sequence are represented.",
            ),
        ],
    )

    assert "positional encodings" in answer
    assert "positions in the sequence" in answer
    assert "softmax layer" not in answer
    assert "[2]" in answer


def test_recommendation_fallback_prefers_explicit_source_guidance() -> None:
    query = "What does the paper recommend for fact-checking and verification?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=26-26\n"
                "For fact-checking, responses should cross-check claims against trusted sources. "
                "When evidence is uncertain, the system should use retrieval-based verification "
                "or abstain rather than invent an answer.",
            ),
            (
                2,
                "[2] doc=doc score=.8 source=bm25 pages=12-12\n"
                "Human evaluation is commonly used to score generated text.",
            ),
        ],
    )

    assert "cross-check claims" in answer
    assert "retrieval-based verification" in answer
    assert "Human evaluation" not in answer
    assert "[1]" in answer


def test_document_workflow_question_may_use_explicit_roadmap_evidence() -> None:
    query = "How does the book place cross-validation in the machine-learning workflow?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=40-40\n"
                "The machine-learning project workflow evaluates shortlisted models with "
                "cross-validation after data preparation and before final model tuning.",
            )
        ],
    )

    assert "after data preparation" in answer
    assert "before final model tuning" in answer
    assert "[1]" in answer


def test_hyphenated_focus_term_does_not_match_only_its_first_word() -> None:
    assert SynthesisService._sentence_score(
        "Learning long-range dependencies is difficult.",
        {"learning-rate"},
    ) == 0
    assert SynthesisService._sentence_score(
        "The learning rate increases during warmup.",
        {"learning-rate"},
    ) == 1
