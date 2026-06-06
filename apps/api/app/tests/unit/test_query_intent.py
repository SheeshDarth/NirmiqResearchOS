from app.domain.query_intent import detect_query_intent


def test_intent_router_detects_summary() -> None:
    intent = detect_query_intent("Summarize this PDF", "research")
    assert intent.intent == "summary"
    assert intent.route == "document_summary"


def test_intent_router_detects_compare() -> None:
    intent = detect_query_intent("Compare transformer attention and CNNs", "research")
    assert intent.intent == "compare"


def test_intent_router_detects_paper_draft() -> None:
    intent = detect_query_intent("Draft a related work section", "research")
    assert intent.intent == "paper_draft"


def test_intent_router_detects_exam_mode() -> None:
    intent = detect_query_intent("Write a 10 mark answer", "exam_answer")
    assert intent.intent == "exam"


def test_intent_router_detects_general_chat_mode() -> None:
    intent = detect_query_intent("Can you help me think?", "general_chat")
    assert intent.intent == "general_chat"
