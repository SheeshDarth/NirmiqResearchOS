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
            "recommendation": "recommendations for",
            "interpretation": "interpret",
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


_ANSWER_EVIDENCE_CUES: dict[str, tuple[str, ...]] = {
    "concept_explanation": (
        " is a ",
        " is an ",
        " refers to ",
        " means ",
        " called ",
        " consists of",
        " composed of",
        " building block",
        " goal is to",
        " used to",
        " allows ",
    ),
    "mechanism_explanation": (
        "works by",
        "operates by",
        "consists of",
        "composed of",
        "for each",
        " then ",
        "compute ",
        "applies ",
        "apply ",
        "computes ",
        "calculates ",
        "calculate ",
        "counts ",
        "count ",
        "divides ",
        "divide ",
        "multiplies ",
        "multiply ",
        "combines ",
        "combine ",
        "adds ",
        "add ",
        "identifies ",
        "identify ",
        "defines ",
        "define ",
        "called ",
        "considered ",
        "belong to",
        "forms ",
        "projects ",
        "project ",
        "transforms ",
        "transform ",
        "passes ",
        "feeds ",
        "connects ",
        "connected ",
        "selects ",
        "assigns ",
        "estimates ",
        "samples ",
        "drops ",
        "drop ",
        "sets ",
        "set ",
        "temporarily ",
        "prevents ",
        "prevent ",
        "ensures ",
        "ensure ",
        "modifies ",
        "modify ",
        "masks ",
        "attend to",
        "based on",
        "means ",
        "indicates ",
        "ranges from",
        "increases ",
        "increasing ",
        "decreases ",
        "decreasing ",
        "ignored ",
        "active ",
        "corresponds to",
    ),
    "procedure": (
        "first ",
        " then ",
        "next ",
        "finally ",
        "step ",
        "start by",
        "followed by",
        "after that",
        "before ",
    ),
    "recommendation": (
        "recommend",
        "should ",
        "cross-check",
        "cross check",
        "verify ",
        "validate ",
        "prefer ",
        "avoid ",
        "fallback",
        "when uncertain",
        "if uncertain",
    ),
    "interpretation": (
        "means ",
        "indicates ",
        "represents ",
        "ranges from",
        "can vary between",
        "close to",
        "value of",
        "corresponds to",
    ),
    "comparison": (
        "whereas",
        "while ",
        "unlike",
        "compared with",
        "compared to",
        "in contrast",
        "difference",
        "higher than",
        "lower than",
        "more than",
        "less than",
        "both ",
    ),
    "limitations": (
        "limitation",
        "drawback",
        "disadvantage",
        "however",
        "cannot ",
        "does not ",
        "doesn't ",
        "fails to",
        "penalty",
        "overhead",
        "slower",
        "risk of",
        "not suitable",
        "does not work",
    ),
}


def answer_evidence_cue_score(answer_type: str, text: str) -> float:
    """Return a bounded linguistic signal for evidence that fits an answer plan."""

    cues = _ANSWER_EVIDENCE_CUES.get(answer_type, ())
    if not cues:
        return 0.0
    normalized = f" {re.sub(r'\s+', ' ', text.lower())} "
    hit_count = sum(1 for cue in cues if cue in normalized)
    if hit_count <= 0:
        return 0.0
    return min(1.0, 0.38 + (0.22 * (hit_count - 1)))


def answer_subject_anchor_terms(query: str, answer_plan: AnswerPlan) -> set[str]:
    """Extract the named subject that answer-bearing evidence must mention."""

    predicate = (
        r"work|compute|represent|identify|regularize|transform|update|mask|reduce|use|"
        r"place|interpret|recommend|apply|select|detect|generate|create|learn|form|encode|"
        r"classify|predict|optimize|train|perform|fit|integrate|relate|connect"
    )
    normalized = re.sub(r"\s+", " ", query.strip())
    document_actor_match = re.match(
        r"^(?:how|why)\s+(?:does|do)\s+(?:the\s+)?"
        r"(?:book|document|module|paper|source|textbook)\s+"
        r"(?:describe|place|explain|present|define|recommend|position|fit|integrate|relate|connect)"
        r"(?:s|ed|ing)?(?![-\w])\s+(.+?)(?:\?|$)",
        normalized,
        flags=re.I,
    )
    match = re.match(
        rf"^(?:how\s+(?:does|do|is|are|should)|why\s+(?:does|do|is|are))\s+(.+?)\s+"
        rf"(?:{predicate})(?:s|ed|ing)?(?![-\w])",
        normalized,
        flags=re.I,
    )
    subject = (
        document_actor_match.group(1)
        if document_actor_match
        else match.group(1)
        if match
        else answer_plan.subject
    )
    if not match and not document_actor_match:
        recommendation_match = re.search(
            r"^what\s+does\s+.+?\b(?:book|document|module|paper|source|textbook)\s+"
            r"recommend(?:s|ed|ing)?(?:\s+(?:for|about|when))?\s+(.+?)(?:\?|$)",
            normalized,
            flags=re.I,
        )
        possession_match = re.search(
            r"\bdoes\s+(.+?)\s+(?:have|provide|offer|cause|add|require)\b",
            normalized,
            flags=re.I,
        )
        relation_match = re.search(
            r"\b(?:limitations?|benefits?|advantages?|drawbacks?)\s+of\s+(.+?)(?:\?|$)",
            normalized,
            flags=re.I,
        )
        if recommendation_match:
            subject = recommendation_match.group(1)
        elif possession_match:
            subject = possession_match.group(1)
        elif relation_match:
            subject = relation_match.group(1)
    # When a document is the grammatical actor, the evidence anchor is the
    # concept being placed or described, not the surrounding workflow.
    subject = re.split(
        r"\s+(?:in|within|during)\s+(?:the\s+)?(?:[a-z0-9+-]+\s+){0,3}workflow\b.*$",
        subject,
        maxsplit=1,
        flags=re.I,
    )[0]
    stopwords = {
        "book",
        "document",
        "module",
        "paper",
        "source",
        "the",
        "this",
        "selected",
        "uploaded",
        "and",
        "about",
        "for",
        "when",
    }
    terms = {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", subject.lower())
        if token not in stopwords
    }
    if terms:
        return terms
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", answer_plan.subject.lower())
        if token not in stopwords
    }


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
    if re.search(r"\b(?:recommend|recommends|recommended|recommendation|recommendations)\b", query):
        return "recommendation"
    if re.search(
        r"\b(?:how\s+to|steps?|procedure|process\s+for|workflow\s+(?:for|of)|"
        r"(?:outline|describe)\b.{0,40}\bworkflow)\b",
        query,
    ):
        return "procedure"
    if re.search(r"\b(limitations?|drawbacks?|disadvantages?|failure\s+cases?|caveats?)\b", query):
        return "limitations"
    if re.search(r"\b(interpret|interprets|interpreted|interpretation|what\s+does\b.+\bmean)\b", query):
        return "interpretation"
    if re.search(
        r"\b(when|who|how\s+many|what\s+year|which\s+year|release\s+date|which\s+edition)\b",
        query,
    ):
        return "factual_lookup"
    if re.search(r"\b(list|name|types?|kinds?|examples?|which)\b", query):
        return "enumeration"
    if re.search(
        r"\b(how\s+does|how\s+do|how\s+is|how\s+should|why\s+does|why\s+do|working|mechanism)\b",
        query,
    ):
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
        ("benefits", r"\b(benefit|benefits|advantage|advantages)\b"),
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
        r"^(?:the\s+)?(?:book|source|document|paper|textbook|module)\s+"
        r"(?:describe|describes|place|places|explain|explains|present|presents|define|defines|recommend|recommends)\s+",
        "",
        subject,
        flags=re.I,
    ).strip()
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
    elif answer_type == "recommendation":
        sections = ["Direct answer", "Recommendations", "When they apply"]
    elif answer_type == "interpretation":
        sections = ["Direct answer", "How to read the value", "Practical meaning"]
    elif answer_type == "limitations":
        sections = ["Direct answer", "Limitations", "When they matter"]
    elif answer_type == "enumeration":
        sections = ["Direct answer", "Requested items with brief explanations"]
    elif answer_type == "mechanism_explanation":
        sections = ["Direct answer", "How it works", "Why it matters"]
    elif answer_type == "concept_explanation":
        sections = ["Direct answer", "How it works"]
    elif answer_type == "factual_lookup":
        sections = ["Direct answer", "Supporting detail"]
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
        "benefits": "Benefits",
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
