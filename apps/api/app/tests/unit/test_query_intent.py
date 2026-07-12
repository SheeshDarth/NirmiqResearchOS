from app.domain.query_intent import detect_query_intent


def test_intent_router_detects_summary() -> None:
    intent = detect_query_intent("Summarize this PDF", "research")
    assert intent.intent == "summary"
    assert intent.route == "document_summary"


def test_intent_router_does_not_let_stale_summary_mode_hijack_specific_question() -> None:
    intent = detect_query_intent("Explain a few unsupervised algorithms from this textbook", "summary")
    assert intent.intent == "factual_lookup"
    assert intent.route == "default_grounded_retrieval"


def test_intent_router_detects_compare() -> None:
    intent = detect_query_intent("Compare transformer attention and CNNs", "research")
    assert intent.intent == "compare"


def test_intent_router_detects_paper_draft() -> None:
    intent = detect_query_intent("Draft a related work section", "research")
    assert intent.intent == "paper_draft"


def test_intent_router_detects_exam_mode() -> None:
    intent = detect_query_intent("Write a 10 mark answer", "exam_answer")
    assert intent.intent == "exam"


def test_intent_router_detects_exam_language_without_exam_mode() -> None:
    intent = detect_query_intent("Write a 10 mark answer from this chapter", "research")
    assert intent.intent == "exam"
    assert intent.route == "exam_grounded"


def test_intent_router_detects_general_chat_mode() -> None:
    intent = detect_query_intent("Can you help me think?", "general_chat")
    assert intent.intent == "general_chat"


def test_intent_router_treats_which_question_as_factual_lookup() -> None:
    intent = detect_query_intent("Which topics does Part I of this textbook cover?", "research")

    assert intent.intent == "factual_lookup"
    assert intent.route == "default_grounded_retrieval"
