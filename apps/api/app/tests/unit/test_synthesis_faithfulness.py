import asyncio

from app.core.config import Settings
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy
from app.services.synthesis_service import SynthesisService


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
