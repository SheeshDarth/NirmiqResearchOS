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


def test_explanation_expansion_does_not_add_generic_format_vocabulary() -> None:
    terms = RetrievalService._query_expansion_terms("Explain CNN")

    assert terms == []


def test_acronym_expansion_keeps_only_the_exact_long_form() -> None:
    chunks = [
        {
            "text": "Convolutional neural networks (CNNs) are used for image recognition.",
            "heading": "CNN Architectures-Choosing the Right CNN Architecture",
            "section_path": "Chapter 14",
        }
    ]

    terms = RetrievalService._document_acronym_expansions(
        query="Explain CNN",
        chunks=chunks,
        sections=[],
    )

    assert terms == ["convolutional", "neural", "networks"]
    assert "architectures" not in terms


def test_acronym_expansion_scans_late_textbook_chunks() -> None:
    chunks = [
        {"text": "General machine learning material.", "heading": "Overview", "section_path": "Part I"}
        for _ in range(1250)
    ]
    chunks.append(
        {
            "text": "Convolutional neural networks (CNNs) process grid-like visual data.",
            "heading": "Convolutional Neural Networks",
            "section_path": "Chapter 14",
        }
    )

    terms = RetrievalService._document_acronym_expansions(
        query="Explain CNN",
        chunks=chunks,
        sections=[],
    )

    assert terms == ["convolutional", "neural", "networks"]


def test_document_acronym_expansion_drives_section_ranking() -> None:
    sections = [
        {
            "id": "generic",
            "heading": "Definitions and Graphs",
            "section_path": "Appendix",
            "key_terms_json": '["definition","graphs"]',
            "page_start": 900,
            "page_end": 901,
        },
        {
            "id": "cnn",
            "heading": "Convolutional Neural Networks",
            "section_path": "Chapter 14 / Convolutional Neural Networks",
            "key_terms_json": '["convolutional","neural","networks"]',
            "page_start": 613,
            "page_end": 635,
        },
    ]
    chunks = [
        {
            "text": "Convolutional neural networks (CNNs) use convolutional and pooling layers.",
            "heading": "Convolutional Neural Networks",
            "section_path": "Chapter 14",
        }
    ]
    terms = RetrievalService._document_aware_expansion_terms(
        query="Explain CNN",
        chunks=chunks,
        sections=sections,
    )

    ranked = RetrievalService._rank_sections(
        RetrievalService._expand_query("Explain CNN", terms),
        sections,
    )

    assert ranked[0]["section_id"] == "cnn"


def test_acronym_expansion_does_not_drift_into_broad_section_terms() -> None:
    sections = [
        {
            "id": "applications",
            "heading": "Examples of Applications",
            "section_path": "Examples of Applications",
            "key_terms_json": '["cnns","purchases","regression","transformers","applications"]',
        }
    ]
    chunks = [
        {
            "text": "Convolutional neural networks (CNNs) are used for image recognition.",
            "heading": "Convolutional Neural Networks",
            "section_path": "Chapter 14",
        }
    ]

    terms = RetrievalService._document_aware_expansion_terms(
        query="Explain CNNs",
        chunks=chunks,
        sections=sections,
    )

    assert terms == ["convolutional", "neural", "networks"]
    assert "applications" not in terms
    assert "purchases" not in terms


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


def test_anchor_rescue_recognizes_definition_named_after_explanation() -> None:
    chunks = [
        {
            "id": "index",
            "page_start": 900,
            "text": "Transfer learning, pretrained models, training APIs, model reuse.",
            "quality_score": 0.8,
        },
        {
            "id": "definition",
            "page_start": 38,
            "text": (
                "Transferring knowledge from one task to another is called transfer learning. "
                "It is especially useful with deep neural networks."
            ),
            "quality_score": 1.0,
        },
    ]

    rescued = RetrievalService._anchor_rescue_candidate_ids(
        query="What is transfer learning?",
        chunks=chunks,
        existing_ids={"index"},
        limit=2,
    )

    assert rescued[0] == "definition"


def test_anchor_rescue_promotes_subject_matched_mechanism_evidence() -> None:
    chunks = [
        {
            "id": "related",
            "text": "Gradient descent is a common optimization algorithm.",
            "heading": "Optimization",
            "section_path": "Overview",
            "chunk_type": "body",
        },
        {
            "id": "mechanism",
            "text": (
                "Gradient descent computes the gradient of the cost function for the model parameters, "
                "then updates the parameters in the opposite direction to reduce the cost."
            ),
            "heading": "Gradient Descent",
            "section_path": "Optimization / Gradient Descent",
            "chunk_type": "body",
        },
    ]

    rescued = RetrievalService._anchor_rescue_candidate_ids(
        query="How does gradient descent update model parameters?",
        chunks=chunks,
        existing_ids={"related"},
        limit=2,
    )

    assert rescued[0] == "mechanism"


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


def test_compact_cross_reference_is_treated_as_index_noise() -> None:
    text = (
        "Convolutional Neural Networks-Semantic Segmentation architectures, "
        "CNN Architectures-Choosing the Right CNN Architecture"
    )

    assert RetrievalService._looks_like_index_chunk(text.lower()) is True


def test_dense_backmatter_cross_references_are_treated_as_index_noise() -> None:
    text = (
        "softmax regression, Softmax Regression-Softmax Regression, SVM classes, "
        "SVM Classes-Computational Complexity, multiclass classification, "
        "Multiclass Classification-Multiclass Classification, convolution kernels, "
        "Filters-CNN Architectures, pooling layers, Pooling Layers-Implementing Pooling Layers, "
        "object detection, Object Detection-You Only Look Once, object tracking, "
        "Object Tracking-Object Tracking, pretrained models, Models-Using Pretrained Models, "
        "semantic segmentation, Segmentation-Semantic Segmentation, model splitting, "
        "Devices-Splitting Across Devices."
    )

    assert RetrievalService._looks_like_index_chunk(text.lower()) is True


def test_sentence_like_chapter_heading_is_treated_as_answer_key_noise() -> None:
    row = {
        "heading": "Chapter 14, convolutional neural networks are far better suited than dense",
        "text": "The encoder is a regular CNN composed of convolutional and pooling layers.",
    }

    assert RetrievalService._looks_like_answer_key_chunk(row) is True


def test_acronym_heading_enters_section_candidates() -> None:
    sections = [
        {
            "id": "intro",
            "heading": "Neural Networks",
            "section_path": "Chapter 14 / Neural Networks",
            "key_terms_json": '["neural","networks"]',
            "page_start": 613,
            "page_end": 615,
        },
        {
            "id": "architecture",
            "heading": "CNN Architectures",
            "section_path": "Chapter 14 / CNN Architectures",
            "key_terms_json": '["layers","pooling","convolutional"]',
            "page_start": 633,
            "page_end": 635,
        },
    ]

    ranked = RetrievalService._rank_sections(
        "Explain CNN convolutional neural networks",
        sections,
    )

    assert {item["section_id"] for item in ranked} == {"intro", "architecture"}
    assert next(item for item in ranked if item["section_id"] == "architecture")["matched_acronyms"] == ["cnn"]


def test_acronym_definition_requires_full_expanded_subject_phrase() -> None:
    query = "Explain CNN convolutional neural networks"
    generic = "The architecture of biological neural networks is the subject of active research."

    assert RetrievalService._specific_query_phrases(query) == ["convolutional neural networks"]
    assert RetrievalService._subject_definition_score(query=query, text=generic) == 0


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


def test_concept_neighbor_rescue_recovers_adjacent_subsection() -> None:
    chunks = [
        {
            "id": "anchor",
            "page_start": 100,
            "text": "Convolutional neural networks use local receptive fields.",
            "quality_score": 1.0,
        },
        {
            "id": "pooling",
            "page_start": 112,
            "text": (
                "The second common building block of CNNs is the pooling layer. "
                "Its goal is to subsample feature maps and reduce computation."
            ),
            "quality_score": 1.0,
        },
        {
            "id": "unrelated",
            "page_start": 105,
            "text": "An optimizer schedule changes the learning rate during training.",
            "quality_score": 1.0,
        },
        {
            "id": "far-away",
            "page_start": 140,
            "text": "CNN pooling layers reduce feature maps.",
            "quality_score": 1.0,
        },
    ]

    rescued = RetrievalService._page_neighbor_rescue_candidate_ids(
        anchor_ids=["anchor"],
        chunks=chunks,
        existing_ids={"anchor"},
        query="Explain CNN convolutional neural networks",
        answer_query="Explain CNN",
        limit=4,
    )

    assert "pooling" in rescued
    assert "unrelated" not in rescued
    assert "far-away" not in rescued
