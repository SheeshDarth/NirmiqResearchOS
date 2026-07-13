from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AnswerPlan:
    answer_type: str
    subject: str
    depth: str
    sections: tuple[str, ...]
    requested_elements: tuple[str, ...]

    def evidence_query(self, original_query: str) -> str:
        if not _needs_evidence_projection(original_query):
            return original_query
        normalized_query = re.sub(r"\W+", " ", original_query).strip().lower()
        normalized_subject = re.sub(r"\W+", " ", self.subject).strip().lower()
        if not normalized_subject or normalized_subject == normalized_query:
            return original_query
        prefixes = {
            "concept_explanation": "explain",
            "mechanism_explanation": "how does",
            "procedure": "how to",
            "limitations": "limitations of",
            "enumeration": "list",
        }
        prefix = prefixes.get(self.answer_type)
        return f"{prefix} {self.subject}" if prefix else self.subject

    def prompt_instruction(self) -> str:
        requested = ", ".join(self.requested_elements) if self.requested_elements else "none"
        structure = " -> ".join(self.sections)
        return (
            "Query-specific answer plan:\n"
            f"- Task: {self.answer_type}\n"
            f"- Subject: {self.subject}\n"
            f"- Depth: {self.depth}\n"
            f"- Requested elements: {requested}\n"
            f"- Preferred structure: {structure}\n"
            "Follow the user's requested scope. Omit a section when the evidence does not support it. "
            "Do not add generic applications, limitations, or background merely because they appear in context."
        )


_LEADING_REQUEST = re.compile(
    r"^(?:please\s+)?(?:can\s+you\s+|could\s+you\s+|would\s+you\s+)?"
    r"(?:what\s+(?:is|are)|how\s+(?:does|do|is|are)|why\s+(?:does|do|is|are)|"
    r"explain|define|describe|summarize|compare|contrast|list|outline|discuss|tell\s+me\s+about)\s+",
    flags=re.I,
)


def _needs_evidence_projection(query: str) -> bool:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    return bool(
        re.search(
            r"\b(in\s+detail|detailed|briefly|clearly|comprehensive|thorough|elaborate)\b",
            normalized,
        )
        or re.search(
            r"\b(?:provide|include|with)\s+(?:image|diagram|figure|visual|citation|source)\s+references?\b",
            normalized,
        )
        or re.search(
            r"\b(?:from|using|according\s+to)\s+(?:this|the|my|selected|uploaded)\s+"
            r"(?:source|document|pdf|paper|textbook|material|notes?)\b",
            normalized,
        )
    )


def build_answer_plan(
    query: str,
    response_mode: str,
    exam_profile: dict[str, object] | None = None,
) -> AnswerPlan:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    mode = response_mode.strip().lower()
    answer_type = _answer_type(normalized, mode)
    depth = _answer_depth(normalized, mode, exam_profile)
    requested = _requested_elements(normalized)
    subject = _subject(query)
    sections = _sections(answer_type, requested, depth)
    return AnswerPlan(
        answer_type=answer_type,
        subject=subject,
        depth=depth,
        sections=sections,
        requested_elements=requested,
    )


def _answer_type(query: str, mode: str) -> str:
    if mode == "research_paper":
        return "academic_draft"
    if mode in {"exam_answer", "revision_notes", "important_questions", "study_guide"}:
        return "exam_response"
    if mode == "summary" or re.search(r"\b(summarize|summary|overview|abstract)\b", query):
        return "document_summary"
    if mode == "compare_concepts" or re.search(r"\b(compare|contrast|difference|differences|versus|vs\.?|distinguish)\b", query):
        return "comparison"
    if re.search(r"\b(how\s+to|steps?|procedure|workflow|process\s+for)\b", query):
        return "procedure"
    if re.search(r"\b(limitations?|drawbacks?|disadvantages?|failure\s+cases?|caveats?)\b", query):
        return "limitations"
    if re.search(r"\b(list|name|types?|kinds?|examples?|which)\b", query):
        return "enumeration"
    if re.search(r"\b(how\s+does|how\s+do|how\s+is|why\s+does|why\s+do|working|mechanism)\b", query):
        return "mechanism_explanation"
    if re.search(r"\b(what\s+is|what\s+are|define|explain|describe|tell\s+me\s+about)\b", query):
        return "concept_explanation"
    if mode == "deep_research":
        return "deep_analysis"
    return "direct_answer"


def _answer_depth(
    query: str,
    mode: str,
    exam_profile: dict[str, object] | None,
) -> str:
    if re.search(r"\b(brief|briefly|concise|short|in\s+one\s+sentence)\b", query):
        return "brief"
    if mode in {"deep_research", "research_paper", "study_guide"} or re.search(
        r"\b(in\s+detail|detailed|deeply|comprehensive|thorough|elaborate)\b",
        query,
    ):
        return "detailed"
    if exam_profile:
        try:
            if int(exam_profile.get("marks") or 0) >= 10:
                return "detailed"
        except (TypeError, ValueError):
            pass
    return "standard"


def _requested_elements(query: str) -> tuple[str, ...]:
    requested: list[str] = []
    patterns = (
        ("examples", r"\b(example|examples|illustrate)\b"),
        ("applications", r"\b(application|applications|use\s+cases?|used\s+for)\b"),
        ("limitations", r"\b(limitation|limitations|drawback|drawbacks|disadvantage|caveat)\b"),
        ("steps", r"\b(step|steps|procedure|workflow|how\s+to)\b"),
        ("diagram references", r"\b(image|images|diagram|diagrams|figure|figures|visual)\b"),
        ("equations", r"\b(equation|equations|formula|formulas|derive|derivation)\b"),
        ("comparison", r"\b(compare|contrast|difference|differences|versus|vs\.?)\b"),
    )
    for label, pattern in patterns:
        if re.search(pattern, query):
            requested.append(label)
    return tuple(requested)


def _subject(query: str) -> str:
    subject = re.sub(r"\s+", " ", query.strip()).strip(" ?.!")
    subject = _LEADING_REQUEST.sub("", subject).strip()
    subject = re.sub(
        r"\b(?:from|using|according\s+to)\s+(?:this|the|my|selected|uploaded)\s+"
        r"(?:source|document|pdf|paper|textbook|material|notes?)\b.*$",
        "",
        subject,
        flags=re.I,
    ).strip(" ,.-")
    subject = re.sub(
        r"\b(?:in\s+detail|briefly|clearly|with\s+(?:image|diagram|figure)\s+references?)\b.*$",
        "",
        subject,
        flags=re.I,
    ).strip(" ,.-")
    return subject or "the user's requested topic"


def _sections(
    answer_type: str,
    requested: tuple[str, ...],
    depth: str,
) -> tuple[str, ...]:
    if answer_type == "document_summary":
        sections = ["Overview", "Main ideas", "Conclusion or limitations when supported"]
    elif answer_type == "comparison":
        sections = ["Direct comparison", "Key differences", "Practical takeaway"]
    elif answer_type == "procedure":
        sections = ["Goal", "Steps", "Why each step matters"]
    elif answer_type == "limitations":
        sections = ["Direct answer", "Limitations", "When they matter"]
    elif answer_type == "enumeration":
        sections = ["Direct answer", "Requested items with brief explanations"]
    elif answer_type == "mechanism_explanation":
        sections = ["Direct answer", "How it works", "Why it matters"]
    elif answer_type == "concept_explanation":
        sections = ["Direct answer", "How it works"]
    elif answer_type == "academic_draft":
        sections = ["Thesis", "Evidence-based discussion", "Limitations", "Conclusion"]
    elif answer_type == "exam_response":
        sections = ["Direct answer", "Marks-aware explanation", "Conclusion"]
    elif answer_type == "deep_analysis":
        sections = ["Finding", "Evidence", "Implications", "Caveats"]
    else:
        sections = ["Direct answer", "Explanation"]

    optional_sections = {
        "examples": "Examples",
        "applications": "Applications",
        "limitations": "Limitations",
        "steps": "Steps",
        "diagram references": "Source diagram references",
        "equations": "Equations",
    }
    for element in requested:
        section = optional_sections.get(element)
        if section and section not in sections:
            sections.append(section)
    if depth == "brief":
        return tuple(sections[:2])
    return tuple(sections)
