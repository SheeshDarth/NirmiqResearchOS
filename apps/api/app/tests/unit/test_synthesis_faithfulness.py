import asyncio

from app.core.config import Settings
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy
from app.services.query_service import QueryService
from app.services.synthesis_service import SynthesisService
from app.domain.query_intent import QueryIntent


class FakeGenerator:
    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.last_backend = "fake"
        self.temperature = 0.0

    async def answer(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        self.last_backend = "fake"
        self.temperature = temperature
        return self._answer


def _settings() -> Settings:
    settings = Settings.from_env()
    return settings.model_copy(update={"use_ollama_generation": False})


def _bundle() -> RetrievalBundle:
    return RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="NIRMIQ uses grounded retrieval and local citation-aware synthesis for academic documents.",
                score=1.0,
                page_start=1,
                page_end=1,
                source="bm25",
            )
        ],
        meta={},
    )


def test_unsupported_cited_generation_is_rewritten_to_grounded_fallback() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator("The moon is made of cheese and NIRMIQ proves it. [1]"),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "moon" not in answer.lower()
    assert "grounded retrieval" in answer.lower()
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert meta["citation_verification_state"] == "supported"
    assert meta["original_unsupported_claims"]


def test_supported_cited_generation_is_preserved() -> None:
    generated = "NIRMIQ uses grounded retrieval and citation-aware synthesis for academic documents. [1]"
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert answer == generated
    assert meta["answer_rewritten_for_faithfulness"] is False
    assert meta["citation_verification_state"] == "supported"
    assert meta["unsupported_claims"] == []


def test_uncited_generated_sentences_are_anchored_to_best_context() -> None:
    generated = "NIRMIQ uses grounded retrieval and citation-aware synthesis for academic documents."
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert answer.endswith("[1]")
    assert meta["citation_coverage"] == 1.0
    assert meta["citation_verification_state"] == "supported"


def test_synthesis_reports_only_answer_cited_context_chunks() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="NIRMIQ stores uploaded material locally for private academic workflows.",
                score=1.0,
                page_start=1,
                page_end=1,
                source="bm25",
            ),
            RetrievedChunk(
                chunk_id="chunk-2",
                document_id="doc-1",
                text="NIRMIQ uses citation-aware synthesis to reduce hallucinated academic answers.",
                score=0.9,
                page_start=2,
                page_end=2,
                source="bm25",
            ),
        ],
        meta={},
    )
    generated = "NIRMIQ uses citation-aware synthesis to reduce hallucinated academic answers. [2]"
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="How does NIRMIQ reduce hallucinations?",
            bundle=bundle,
            response_mode="research",
        )
    )

    assert grounded is True
    assert answer == generated
    assert meta["selected_context_chunk_ids"] == ["chunk-1", "chunk-2"]
    assert meta["cited_context_chunk_ids"] == ["chunk-2"]
    assert meta["citation_anchor_chunk_map"] == [
        {
            "anchor": 2,
            "chunk_id": "chunk-2",
            "document_id": "doc-1",
            "page_start": 2,
            "page_end": 2,
        }
    ]


def test_query_citations_are_limited_to_synthesis_used_chunks() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="unused",
                document_id="doc-1",
                text="This chunk was retrieved but not cited by the final answer.",
                score=1.0,
            ),
            RetrievedChunk(
                chunk_id="used",
                document_id="doc-1",
                text="This chunk directly supports the final answer.",
                score=0.8,
            ),
        ],
        meta={},
    )

    citations = QueryService._citations_from_synthesis_context(
        bundle,
        {"cited_context_chunk_ids": ["used"]},
        grounded=True,
    )

    assert [citation.chunk_id for citation in citations] == ["used"]
    assert citations[0].excerpt == "This chunk directly supports the final answer."


def test_factual_retrieval_query_expands_unsupervised_algorithm_terms() -> None:
    query = "Explain a few unsupervised algorithms from this textbook"
    expanded = QueryService._retrieval_query(
        query,
        "research",
        {"questions": [], "diagrams": []},
        QueryIntent("factual_lookup", 0.68, "default_grounded_retrieval"),
    )

    assert expanded != query
    assert "clustering" in expanded.lower()
    assert "anomaly detection" in expanded.lower()


def test_fallback_list_answer_uses_compact_answer_contract() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(""),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text=(
                    "Unsupervised learning techniques include clustering, density estimation, "
                    "dimensionality reduction, and anomaly detection."
                ),
                score=1.0,
                page_start=1,
                page_end=1,
                source="bm25",
            )
        ],
        meta={},
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="Explain a few unsupervised algorithms",
            bundle=bundle,
            response_mode="research",
        )
    )

    assert grounded is True
    assert "Direct answer" in answer
    assert "Key points" in answer
    assert "clustering" in answer.lower()
    assert meta["citation_coverage"] >= 0.5


def test_any_unsupported_cited_claim_forces_rewrite() -> None:
    generated = (
        "NIRMIQ uses grounded retrieval for academic documents. [1]\n"
        "NIRMIQ is also a cloud payments platform with social analytics. [1]\n"
        "NIRMIQ uses citation-aware synthesis. [1]"
    )
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "cloud payments" not in answer.lower()
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert len(meta["original_unsupported_claims"]) >= 1


def test_unsupported_uncited_generation_does_not_receive_fabricated_anchor() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator("Quantum bananas calculate ocean treaties."),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "quantum bananas" not in answer.lower()
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert meta["citation_verification_state"] == "supported"


def test_low_citation_coverage_fails_evidence_reliability_gate() -> None:
    generated = (
        "NIRMIQ uses grounded retrieval for academic documents. [1]\n"
        "The system guarantees perfect answers forever."
    )
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is False
    assert "not enough source-backed evidence" in answer
    assert meta["evidence_gate_state"] == "failed"
    assert "low_citation_coverage" in meta["evidence_gate_reasons"]
    assert meta["citation_coverage"] < meta["evidence_gate_min_citation_coverage"]


def test_long_context_deep_research_uses_configured_creative_temperature() -> None:
    generator = FakeGenerator("NIRMIQ uses grounded retrieval and citation-aware synthesis. [1]")
    service = SynthesisService(
        settings=_settings().model_copy(
            update={
                "generator_temperature_grounded": 0.15,
                "generator_temperature_long_context": 0.85,
            }
        ),
        policy=RetrievalPolicy(min_grounding_score=0.1, max_context_tokens=2000),
        generator=generator,  # type: ignore[arg-type]
    )
    repeated_text = (
        "NIRMIQ uses grounded retrieval and local citation-aware synthesis for academic documents. "
        * 120
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text=repeated_text,
                score=1.0,
                page_start=1,
                page_end=2,
                source="bm25",
            )
        ],
        meta={},
    )

    _, grounded, meta = asyncio.run(
        service.synthesize(
            query="Write deep research notes.",
            bundle=bundle,
            response_mode="deep_research",
        )
    )

    assert grounded is True
    assert generator.temperature == 0.85
    assert meta["generation_temperature"] == 0.85
