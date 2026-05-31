import asyncio

from app.core.config import Settings
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy
from app.services.synthesis_service import SynthesisService


class FakeGenerator:
    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.last_backend = "fake"

    async def answer(self, prompt: str, model: str | None = None) -> str:
        self.last_backend = "fake"
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
