import json

from app.api.schemas.query import QueryRequest
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.query_intent import QueryIntent
from app.services.query_service import QueryService
from app.services.retrieval_service import RetrievalService
from app.services.synthesis_service import SynthesisService


class _FakeChunkRepo:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def get_document_chunks(self, document_id: str, active_only: bool = True) -> list[dict[str, object]]:
        return self._rows


def test_definition_seed_prefers_definition_over_keyword_mentions() -> None:
    query = "What is a Gaussian mixture model?"
    focus_terms = QueryService._query_focus_terms(query)
    definition_row = {
        "text": (
            "Gaussian Mixtures A Gaussian mixture model (GMM) is a probabilistic model "
            "that assumes instances were generated from a mixture of several Gaussian "
            "distributions whose parameters are unknown."
        ),
        "heading": "Gaussian Mixtures",
        "section_path": "Gaussian Mixtures",
        "chunk_type": "definition",
        "quality_score": 0.9,
    }
    mention_row = {
        "text": (
            "We will discuss Gaussian mixture models and see how they can be used for "
            "density estimation, clustering, and anomaly detection."
        ),
        "heading": "An Example",
        "section_path": "An Example",
        "chunk_type": "definition",
        "quality_score": 0.9,
    }

    definition_score = QueryService._factual_seed_score(definition_row, query, focus_terms)
    mention_score = QueryService._factual_seed_score(mention_row, query, focus_terms)

    assert definition_score > mention_score


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


def test_factual_seed_promotes_existing_definition_chunk_to_front() -> None:
    definition_row = {
        "id": "definition",
        "document_id": "doc-1",
        "text": (
            "Gaussian Mixtures A Gaussian mixture model (GMM) is a probabilistic model "
            "that assumes instances were generated from Gaussian distributions."
        ),
        "page_start": 357,
        "page_end": 357,
        "quality_score": 0.9,
        "section_id": "section-1",
        "heading": "Gaussian Mixtures",
        "section_path": "Gaussian Mixtures",
        "chunk_type": "definition",
    }
    weaker_row = {
        **definition_row,
        "id": "mention",
        "text": "Gaussian mixture models can be used for density estimation and clustering.",
        "heading": "An Example",
        "section_path": "An Example",
    }
    service = QueryService(
        memory_service=object(),  # type: ignore[arg-type]
        retrieval_service=object(),  # type: ignore[arg-type]
        synthesis_service=object(),  # type: ignore[arg-type]
        sqlite_repo=_FakeChunkRepo([weaker_row, definition_row]),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(chunk_id="mention", document_id="doc-1", text=str(weaker_row["text"]), score=0.9),
            RetrievedChunk(chunk_id="definition", document_id="doc-1", text=str(definition_row["text"]), score=0.8),
        ]
    )

    augmented = service._augment_selected_factual_bundle(
        payload=QueryRequest(
            session_id="test",
            query="What is a Gaussian mixture model?",
            document_id="doc-1",
        ),
        intent=QueryIntent("factual_lookup", 0.8, "default_grounded_retrieval"),
        bundle=bundle,
    )

    assert augmented.chunks[0].chunk_id == "definition"
    assert [chunk.chunk_id for chunk in augmented.chunks].count("definition") == 1
