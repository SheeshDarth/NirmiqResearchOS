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


def test_clean_evidence_sentence_removes_golden_demo_heading_prefix() -> None:
    cleaned = SynthesisService._clean_evidence_sentence(
        "# Golden Demo Source 02: Offline Runtime And Privacy NIRMIQ is local-first."
    )

    assert cleaned == "NIRMIQ is local-first."

