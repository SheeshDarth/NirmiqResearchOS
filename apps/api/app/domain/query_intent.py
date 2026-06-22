from dataclasses import dataclass
import re


@dataclass(frozen=True)
class QueryIntent:
    intent: str
    confidence: float
    route: str


_EXAM_MODES = {"exam_answer", "revision_notes", "important_questions", "compare_concepts", "study_guide"}


def detect_query_intent(query: str, mode: str) -> QueryIntent:
    normalized_mode = mode.strip().lower()
    normalized_query = query.strip().lower()
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", normalized_query))

    if _is_summary_request(normalized_query, tokens, normalized_mode):
        return QueryIntent("summary", 0.95 if normalized_mode == "summary" else 0.85, "document_summary")
    if normalized_mode in _EXAM_MODES:
        return QueryIntent("exam", 0.95, "exam_grounded")
    if normalized_mode == "research_paper" or _has_phrase(
        normalized_query, ("research paper", "related work", "methodology", "paper section")
    ):
        return QueryIntent("paper_draft", 0.92, "paper_grounded")
    if normalized_mode == "deep_research" or _has_phrase(
        normalized_query, ("deep research", "detailed analysis", "research analysis")
    ):
        return QueryIntent("deep_research", 0.9, "deep_grounded")
    if normalized_mode == "compare_concepts" or _has_any(tokens, {"compare", "contrast", "difference", "differences"}):
        return QueryIntent("compare", 0.88, "comparison_grounded")
    if normalized_mode == "general_chat":
        return QueryIntent("general_chat", 0.8, "local_chat")
    if _has_any(tokens, {"what", "why", "how", "when", "where", "define", "explain"}):
        return QueryIntent("factual_lookup", 0.68, "default_grounded_retrieval")
    return QueryIntent("unanswerable_or_unclear", 0.45, "abstain_if_weak")


def _has_any(tokens: set[str], candidates: set[str]) -> bool:
    return bool(tokens & candidates)


def _has_phrase(value: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in value for phrase in phrases)


def _is_summary_request(normalized_query: str, tokens: set[str], normalized_mode: str) -> bool:
    if _has_any(tokens, {"summarize", "summary", "overview", "abstract"}):
        return True
    if normalized_mode != "summary":
        return False
    # The UI can remain in summary mode after a one-click summary. Do not let that
    # hijack specific follow-up questions like "explain unsupervised algorithms".
    specific_question_terms = {
        "algorithm",
        "algorithms",
        "compare",
        "contrast",
        "define",
        "difference",
        "differences",
        "example",
        "examples",
        "explain",
        "how",
        "list",
        "why",
    }
    if tokens & specific_question_terms and not _has_phrase(
        normalized_query,
        (
            "summarize this",
            "summary of",
            "overview of",
            "what is this about",
            "what is it about",
            "explain this pdf",
            "explain the pdf",
            "explain this document",
            "explain the document",
            "explain this material",
            "explain the material",
        ),
    ):
        return False
    document_level_terms = {"pdf", "document", "file", "material", "paper", "textbook"}
    return bool(tokens & document_level_terms) or normalized_query in {"explain", "what is this", "what is it about"}
