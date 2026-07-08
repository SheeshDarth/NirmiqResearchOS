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
