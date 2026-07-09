from app.services.retrieval_service import RetrievalService


def test_query_expansion_adds_positional_encoding_terms() -> None:
    expanded = RetrievalService._expand_query("How does the Transformer represent token positions?")

    assert "positional" in expanded
    assert "encodings" in expanded
    assert "embeddings" in expanded


def test_query_expansion_adds_privacy_terms() -> None:
    expanded = RetrievalService._expand_query("What privacy protections are listed for generative AI workflows?")

    assert "personal" in expanded
    assert "information" in expanded
    assert "retention" in expanded
    assert "sensive" in expanded
    assert "retenon" in expanded
    assert "hyperparameters" not in expanded


def test_explanatory_queries_penalize_index_like_chunks() -> None:
    index_row = {
        "text": (
            "Vision Transformers visual cortex architecture, WaveNet copy.deepcopy(), "
            "Early Stopping core instance, DBSCAN correlation coefficient, "
            "cost function, Model-based learning, cross-validation, SVM, "
            "Random forests, ensemble methods, logistic regression, linear regression, "
            "polynomial regression, k-nearest neighbors, decision trees"
        ),
        "heading": "Index",
        "section_path": "Index",
        "chunk_type": "body",
    }
    body_row = {
        "text": "Cross-validation helps evaluate models by training and validating on different folds.",
        "heading": "Hyperparameter Tuning and Model Selection",
        "section_path": "Chapter 2",
        "chunk_type": "body",
    }

    query = "How does the book describe cross-validation in the machine learning workflow?"

    assert RetrievalService._chunk_noise_penalty(row=index_row, query=query) > 0.25
    assert RetrievalService._chunk_noise_penalty(row=body_row, query=query) == 0.0


def test_query_expansion_uses_document_acronym_definitions() -> None:
    chunks = [
        {
            "text": "Convolutional neural networks (CNNs) are widely used for image recognition tasks.",
            "heading": "Convolutional Neural Networks",
            "section_path": "Chapter 14",
        }
    ]

    terms = RetrievalService._query_expansion_terms("Explain CNNs in detail", chunks=chunks, sections=[])

    assert "convolutional" in terms
    assert "neural" in terms
    assert "networks" in terms


def test_direct_evidence_score_prefers_answer_passage_over_loose_mention() -> None:
    direct_row = {
        "text": "Convolutional neural networks use convolutional layers to detect visual patterns in images.",
        "heading": "Convolutional Neural Networks",
        "section_path": "Chapter 14",
        "chunk_type": "body",
    }
    loose_row = {
        "text": "Image recognition is one possible application among many other machine learning tasks.",
        "heading": "Examples of Applications",
        "section_path": "Chapter 1",
        "chunk_type": "body",
    }
    query = "Explain convolutional neural networks in detail"

    assert RetrievalService._chunk_answer_relevance(row=direct_row, query=query) > RetrievalService._chunk_answer_relevance(row=loose_row, query=query)


def test_anchor_rescue_promotes_direct_definition_from_legacy_chunks() -> None:
    chunks = [
        {
            "id": "loose",
            "text": (
                "Gaussian mixtures, Bayesian Gaussian mixtures, Bayesian information criterion, "
                "beam search, Bellman equation, and other index entries."
            ),
            "heading": "Index",
            "section_path": "Index",
            "chunk_type": "body",
        },
        {
            "id": "direct",
            "text": (
                "A Gaussian mixture model is a probabilistic model that assumes instances were "
                "generated from a mixture of several Gaussian distributions with unknown parameters."
            ),
            "heading": "Gaussian Mixtures",
            "section_path": "Chapter 9 / Gaussian Mixtures",
            "chunk_type": "body",
        },
    ]

    rescued = RetrievalService._anchor_rescue_candidate_ids(
        query="What is a Gaussian mixture model?",
        chunks=chunks,
        existing_ids={"loose"},
        limit=2,
    )

    assert rescued[0] == "direct"


def test_exercise_question_chunks_are_noisy_for_explanations() -> None:
    row = {
        "text": (
            "1. What is a Gaussian mixture? What tasks can you use it for? "
            "2. Can you name two techniques to find the number of clusters?"
        ),
        "heading": "Exercises",
        "section_path": "Exercises",
        "chunk_type": "body",
    }

    assert RetrievalService._chunk_noise_penalty(row=row, query="What is a Gaussian mixture model?") > 0


def test_section_ranking_boosts_exact_query_phrase_without_topic_specific_rule() -> None:
    sections = [
        {
            "id": "broad",
            "heading": "Examples of Applications",
            "section_path": "Chapter 1",
            "key_terms_json": '["image","recognition","applications"]',
            "page_start": 12,
            "page_end": 14,
        },
        {
            "id": "direct",
            "heading": "Image Recognition",
            "section_path": "Computer Vision / Image Recognition",
            "key_terms_json": '["image","recognition","visual"]',
            "page_start": 220,
            "page_end": 224,
        },
    ]

    ranked = RetrievalService._rank_sections("Explain image recognition software", sections)

    assert ranked[0]["section_id"] == "direct"
