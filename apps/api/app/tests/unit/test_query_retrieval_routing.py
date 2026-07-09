from app.domain.query_intent import QueryIntent
from app.services.query_service import QueryService


def test_attached_source_default_routes_to_bm25_first() -> None:
    intent = QueryIntent("factual_lookup", 0.8, "default_grounded_retrieval")

    mode = QueryService._resolve_retrieval_mode(
        mode="research",
        retrieval_mode="hybrid",
        document_id="doc-1",
        intent=intent,
    )

    assert mode == "bm25"


def test_explicit_vector_mode_is_preserved() -> None:
    intent = QueryIntent("factual_lookup", 0.8, "default_grounded_retrieval")

    mode = QueryService._resolve_retrieval_mode(
        mode="research",
        retrieval_mode="vector",
        document_id="doc-1",
        intent=intent,
    )

    assert mode == "vector"
