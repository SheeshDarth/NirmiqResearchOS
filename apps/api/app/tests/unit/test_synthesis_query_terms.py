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

