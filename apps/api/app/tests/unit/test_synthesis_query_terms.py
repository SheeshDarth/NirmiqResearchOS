from app.domain.models import RetrievalBundle, RetrievedChunk
from app.services.synthesis_service import SynthesisService


def test_synthesis_query_terms_expand_token_positions() -> None:
    terms = SynthesisService._query_terms("How does the Transformer represent token positions?")

    assert "positional" in terms
    assert "encodings" in terms
    assert "embeddings" in terms


def test_synthesis_query_terms_expand_multi_head_attention() -> None:
    terms = SynthesisService._query_terms("Why does the paper use multi-head attention?")

    assert "representation" in terms
    assert "subspaces" in terms
    assert "positions" in terms


def test_synthesis_query_terms_expand_privacy_language() -> None:
    terms = SynthesisService._query_terms("What privacy protections are listed for generative AI workflows?")

    assert "personal" in terms
    assert "information" in terms
    assert "retention" in terms


def test_synthesis_query_terms_expand_hardware_and_duration_language() -> None:
    terms = SynthesisService._query_terms(
        "What hardware and training duration are reported for the base Transformer model?"
    )

    assert "machine" in terms
    assert "gpu" in terms
    assert "hours" in terms
    assert "steps" in terms


def test_synthesis_query_terms_expand_fact_checking_language() -> None:
    terms = SynthesisService._query_terms(
        "What does the module recommend for fact-checking and verification?"
    )

    assert "trusted" in terms
    assert "retrieval" in terms
    assert "fallback" in terms


def test_context_relevance_uses_acronym_expansion_from_retrieved_context() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="cnn",
                document_id="doc",
                text="Convolutional neural networks (CNNs) use convolutional layers for visual pattern recognition.",
                score=0.9,
            )
        ]
    )

    relevance = SynthesisService._context_relevance("Explain CNNs in detail", bundle)

    assert relevance["answer_relevance_state"] == "direct"
    assert relevance["direct_evidence_count"] == 1


def test_context_relevance_does_not_treat_lone_acronym_mention_as_definition() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="cnn-application",
                document_id="doc",
                text=(
                    "The CNN was trained to predict class probabilities, a bounding box, "
                    "and an objectness score for object detection."
                ),
                score=0.9,
            )
        ]
    )

    relevance = SynthesisService._context_relevance("Explain CNN", bundle)

    assert relevance["primary_query_terms"] == ["cnn"]
    assert relevance["answer_relevance_state"] == "weak_related"
    assert relevance["direct_evidence_count"] == 0


def test_definition_fallback_uses_acronym_definition_without_false_limitation() -> None:
    context_chunks = [
        (
            1,
            "[1] doc=doc score=1.000 source=bm25 pages=613-615\n"
            "Convolutional neural networks (CNNs) emerged from the study of the brain's visual cortex, "
            "and they have been used in computer image recognition since the 1980s. CNNs are not "
            "restricted to visual perception; they are also successful at voice recognition and NLP.",
        ),
        (
            2,
            "[2] doc=doc score=0.900 source=bm25 pages=633-634\n"
            "Typical CNN architectures stack a few convolutional layers followed by pooling layers, "
            "then add fully connected layers for the final prediction.",
        ),
    ]

    answer = SynthesisService._fallback_definition_answer(
        query="Explain CNN",
        context_chunks=context_chunks,
        response_mode="research",
    )

    assert "Convolutional neural networks (CNNs)" in answer
    assert "Typical CNN architectures stack" in answer
    assert "\nLimitation\n" not in answer


def test_context_relevance_marks_loose_mentions_as_weak_related() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="mention",
                document_id="doc",
                text="Image recognition is one possible application of machine learning.",
                score=0.9,
            )
        ]
    )

    relevance = SynthesisService._context_relevance("Explain image recognition software in detail", bundle)

    assert relevance["answer_relevance_state"] == "weak_related"
    assert relevance["direct_evidence_count"] == 0


def test_context_relevance_treats_local_privacy_controls_as_direct_evidence() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="privacy",
                document_id="doc",
                text=(
                    "NIRMIQ is local-first. Uploaded files are stored under the local data directory. "
                    "Direct local-path ingestion is restricted to trusted corpus roots, and a selected "
                    "document can be removed from the local library, clearing its metadata and chunks."
                ),
                score=0.9,
            )
        ]
    )

    relevance = SynthesisService._context_relevance(
        "How does NIRMIQ preserve local-first privacy during document work?",
        bundle,
    )

    assert relevance["answer_relevance_state"] == "direct"
    assert relevance["direct_evidence_count"] == 1


def test_context_relevance_normalizes_ocr_glyphs_before_scoring() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="fact-checking",
                document_id="doc",
                text=(
                    "Fact-Checking and VerificaƟon. Cross-check outputs with trusted sources. "
                    "Use retrieval-based methods and return fallback responses if uncertain."
                ),
                score=0.9,
            )
        ]
    )

    relevance = SynthesisService._context_relevance(
        "What does the module recommend for fact-checking and verification?",
        bundle,
    )

    assert relevance["answer_relevance_state"] == "direct"
    assert relevance["direct_evidence_count"] == 1


def test_privacy_control_fallback_extracts_concrete_local_controls() -> None:
    context_chunks = [
        (
            1,
            "[1] doc=doc score=1.000 source=bm25 pages=1-1\n"
            "NIRMIQ is local-first. Uploaded files are stored under the local data directory. "
            "Direct local-path ingestion is restricted to trusted corpus roots, which prevents accidental indexing of private folders. "
            "Uploaded file signatures are checked so a renamed file cannot easily masquerade as a PDF or image. "
            "A selected document can be removed from the local library, clearing its metadata, chunks, and vector entries.",
        )
    ]

    answer = SynthesisService._fallback_privacy_control_answer(
        "How does NIRMIQ preserve local-first privacy during document work?",
        context_chunks,
    )

    assert "Privacy controls" in answer
    assert "local data directory" in answer
    assert "trusted corpus roots" in answer
    assert "file signatures" in answer
    assert "[1]" in answer


def test_privacy_control_fallback_handles_general_document_controls() -> None:
    context_chunks = [
        (
            1,
            "[1] doc=doc score=1.000 source=bm25 pages=26-26\n"
            "Privacy Protection  Avoid storing sensiƟve user data  Mask personal informaƟon (PII) "
            " Use encrypƟon and secure APIs  Limit data retenƟon.",
        )
    ]

    answer = SynthesisService._fallback_privacy_control_answer(
        "What privacy protections are listed for generative AI workflows?",
        context_chunks,
    )

    assert "sensitive user data" in answer.lower()
    assert "personal information" in answer.lower()
    assert "encryption" in answer.lower()
    assert "data retention" in answer.lower()
    assert "NIRMIQ preserves privacy" not in answer
    assert "[1]" in answer


def test_textbook_outline_is_not_filtered_as_backmatter_noise() -> None:
    outline = (
        "Part I, The Fundamentals of Machine Learning, covers the following topics: "
        "framing the problem and looking at the big picture, preparing data, selecting a model, "
        "tuning hyperparameters using cross-validation, and handling underfitting and overfitting."
    )

    assert SynthesisService._is_low_value_evidence_sentence(outline) is False


def test_fallback_prefers_direct_cross_validation_outline_over_generic_workflow_text() -> None:
    answer = SynthesisService._fallback_answer(
        query="How does the book describe cross-validation in the machine learning workflow?",
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1.000 source=bm25 pages=44-44\n"
                "Model-based learning builds a model from examples and uses it to make predictions.",
            ),
            (
                2,
                "[2] doc=doc score=0.900 source=bm25 pages=8-8\n"
                "Part I covers the following topics: selecting a model and tuning hyperparameters "
                "using cross-validation, then handling underfitting and overfitting.",
            ),
        ],
        response_mode="research",
    )

    assert "selecting a model and tuning hyperparameters using cross-validation" in answer.lower()
    assert "[2]" in answer


def test_clean_evidence_sentence_removes_golden_demo_heading_prefix() -> None:
    cleaned = SynthesisService._clean_evidence_sentence(
        "# Golden Demo Source 02: Offline Runtime And Privacy NIRMIQ is local-first."
    )

    assert cleaned == "NIRMIQ is local-first."

