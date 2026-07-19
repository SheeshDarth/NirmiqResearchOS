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


def test_factual_lookup_does_not_mix_answer_format_words_into_retrieval() -> None:
    intent = QueryIntent("factual_lookup", 0.8, "default_grounded_retrieval")

    query = QueryService._retrieval_query("explain CNN", "research", {}, intent)

    assert query == "explain CNN"
    assert "limitations" not in query
    assert "key points" not in query


def test_comparison_retrieval_keeps_the_users_named_sides_focused() -> None:
    intent = QueryIntent("compare", 0.9, "comparison_retrieval")
    query = "Compare precision and recall for a binary classifier."

    focused = QueryService._retrieval_query(query, "compare_concepts", {}, intent)

    assert focused == query
    assert "tradeoffs advantages limitations" not in focused
