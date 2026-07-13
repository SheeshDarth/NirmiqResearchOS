import json

from app.services.retrieval_service import RetrievalService
from app.services.synthesis_service import SynthesisService


def test_definition_query_ranks_real_section_before_backmatter_index() -> None:
    ranked = RetrievalService._rank_sections(
        "What is a Gaussian mixture model?",
        [
            {
                "id": "exact",
                "heading": "Gaussian Mixtures",
                "section_path": "Gaussian Mixtures",
                "page_start": 357,
                "page_end": 357,
                "key_terms_json": json.dumps(["gaussian", "mixture", "model", "probabilistic", "cluster"]),
            },
            {
                "id": "index",
                "heading": "Bayesian Gaussian mixtures, Bayesian Gaussian Mixture Models",
                "section_path": "Bayesian Gaussian mixtures, Bayesian Gaussian Mixture Models",
                "page_start": 1027,
                "page_end": 1027,
                "key_terms_json": json.dumps(["bayesian", "gaussian", "mixture", "models", "beam", "bellman"]),
            },
        ],
    )

    assert ranked[0]["section_id"] == "exact"


def test_low_value_evidence_filter_rejects_index_fragments() -> None:
    bad_sentence = (
        "Bayesian Gaussian mixtures, Bayesian Gaussian Mixture Models fast-MCD, "
        "Other Algorithms for Anomaly and Novelty Detection inverse_transform() with PCA, "
        "Beam Search, Bellman optimality equation."
    )
    good_sentence = (
        "A Gaussian mixture model is a probabilistic model that assumes instances were "
        "generated from a mixture of several Gaussian distributions."
    )

    assert SynthesisService._is_low_value_evidence_sentence(bad_sentence) is True
    assert SynthesisService._is_low_value_evidence_sentence(good_sentence) is False


def test_fallback_definition_answer_uses_definition_not_index_fragment() -> None:
    context_chunks = [
        (
            1,
            "[1] doc=doc score=0.9 source=bm25 pages=1027-1027\n"
            "Bayesian Gaussian mixtures, Bayesian Gaussian Mixture Models fast-MCD, "
            "Other Algorithms for Anomaly and Novelty Detection inverse_transform() with PCA, "
            "Beam Search, Bellman optimality equation.",
        ),
        (
            2,
            "[2] doc=doc score=0.9 source=bm25 pages=357-357\n"
            "Gaussian Mixtures A Gaussian mixture model (GMM) is a probabilistic model "
            "that assumes that the instances were generated from a mixture of several "
            "Gaussian distributions whose parameters are unknown. Each cluster can have "
            "a different ellipsoidal shape, size, density, and orientation.",
        ),
        (
            3,
            "[3] doc=doc score=0.8 source=bm25 pages=359-362\n"
            "A Gaussian mixture model is a generative model, meaning you can sample new "
            "instances from it. It is also possible to estimate the density of the model "
            "at any given location.",
        ),
    ]

    answer = SynthesisService._fallback_definition_answer(
        query="What is a Gaussian mixture model?",
        context_chunks=context_chunks,
        response_mode="research",
    )

    assert "probabilistic model" in answer.lower()
    assert "generated from a mixture" in answer.lower()
    assert "beam search" not in answer.lower()
    assert "Direct answer" in answer


def test_fallback_definition_prefers_subject_called_definition() -> None:
    context_chunks = [
        (
            1,
            "[1] doc=doc score=1.0 source=bm25 pages=20-20\n"
            "Constraining a model to make it simpler and reduce the risk of overfitting is called regularization.",
        ),
        (
            2,
            "[2] doc=doc score=0.9 source=bm25 pages=30-30\n"
            "Ridge regression, also called Tikhonov regularization, is a regularized version of linear regression.",
        ),
    ]

    answer = SynthesisService._fallback_definition_answer(
        query="What is regularization in the context of reducing overfitting?",
        context_chunks=context_chunks,
        response_mode="research",
    )

    assert "Constraining a model to make it simpler" in answer
    assert "Direct answer\n- Ridge regression" not in answer
