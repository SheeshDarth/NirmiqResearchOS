from dataclasses import dataclass
import re


@dataclass(frozen=True)
class EvidenceObligation:
    """A query-derived evidence slot that must be filled from source text."""

    key: str
    label: str
    retrieval_terms: tuple[str, ...]
    evidence_cues: tuple[str, ...]
    required: bool = True


@dataclass(frozen=True)
class AnswerPlan:
    answer_type: str
    subject: str
    depth: str
    sections: tuple[str, ...]
    requested_elements: tuple[str, ...]
    evidence_obligations: tuple[EvidenceObligation, ...]

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
        obligations = ", ".join(
            f"{item.label}{'' if item.required else ' (optional)'}"
            for item in self.evidence_obligations
        ) or "direct source support"
        return (
            "Query-specific answer plan:\n"
            f"- Task: {self.answer_type}\n"
            f"- Subject: {self.subject}\n"
            f"- Depth: {self.depth}\n"
            f"- Requested elements: {requested}\n"
            f"- Evidence obligations: {obligations}\n"
            f"- Preferred structure: {structure}\n"
            "Follow the user's requested scope. Omit a section when the evidence does not support it. "
            "Do not add generic applications, limitations, or background merely because they appear in context."
        )

    def evidence_queries(self, original_query: str) -> dict[str, str]:
        """Build bounded lexical searches for each evidence obligation."""

        queries: dict[str, str] = {}
        for obligation in self.evidence_obligations[:4]:
            terms = " ".join(obligation.retrieval_terms)
            queries[obligation.key] = " ".join(
                part.strip()
                for part in (original_query, self.subject, terms)
                if part.strip()
            )
        return queries


def evidence_obligation_score(obligation: EvidenceObligation, text: str) -> float:
    """Score generic obligation cues without encoding benchmark topics."""

    normalized = f" {re.sub(r'[^a-zA-Z0-9_-]+', ' ', text.lower()).strip()} "
    text_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", normalized))
    normalized_text_terms = {_obligation_term_stem(term) for term in text_terms}
    term_hits = sum(
        1
        for term in obligation.retrieval_terms
        if _obligation_term_stem(term) in normalized_text_terms
    )
    if obligation.key.startswith("comparison_side_"):
        comparison_text = f" {re.sub(r'\s+', ' ', text.lower()).strip()} "
        cue_hits = _local_comparison_cue_hits(obligation, comparison_text)
    else:
        cue_hits = sum(1 for cue in obligation.evidence_cues if cue in normalized)
    if obligation.key.startswith(("result_target_", "operation_focus", "comparison_side_")) and term_hits <= 0:
        return 0.0
    if cue_hits <= 0 and term_hits <= 0:
        return 0.0
    return min(1.0, (0.42 * min(cue_hits, 2)) + (0.1 * min(term_hits, 3)))


def _local_comparison_cue_hits(obligation: EvidenceObligation, text: str) -> int:
    """Only credit comparison cues that describe the requested side locally."""

    normalized_terms = tuple(dict.fromkeys(term.lower() for term in obligation.retrieval_terms))
    definition_relation_pattern = (
        r"(?:is\s+(?:a|an|the)\b|measures?\b|means?\b|refers?\s+to\b|"
        r"represents?\b|indicates?\b)"
    )
    action_relation_pattern = (
        r"(?:adapts?\b|(?<!-)learns?\b|sensitive\b|causes?\b|makes?\b|has\b|have\b|"
        r"should\b|must\b|requires?\b|uses?\b|triggers?\b|leads?\s+to\b|results?\s+in\b)"
    )
    broad_action_terms = {"high", "low", "higher", "lower", "fast", "slow"}
    clauses = [
        clause.strip()
        for clause in re.split(r"[.;:!?]|\b(?:whereas|while|but)\b", text)
        if clause.strip()
    ]
    relation_hits = 0
    called_hits = 0
    structured_row_hits = 0
    for term in normalized_terms:
        escaped_term = re.escape(term)
        action_gap = 12 if term in broad_action_terms else 4
        relation_hits += int(
            any(
                bool(
                    re.search(
                        rf"\b{escaped_term}\b(?:\W+[a-z0-9_-]+){{0,4}}\W+"
                        rf"{definition_relation_pattern}",
                        clause,
                    )
                    or re.search(
                        rf"\b{escaped_term}\b(?:\W+[a-z0-9_-]+){{0,{action_gap}}}\W+"
                        rf"{action_relation_pattern}",
                        clause,
                    )
                )
                for clause in clauses
            )
        )
        called_hits += int(
            any(
                re.search(
                    rf"(?:\bis\s+)?\bcalled\s+(?:the\s+)?\b{escaped_term}\b(?!\s*/)|"
                    rf"\b{escaped_term}\b\s*,\s*(?:also\s+)?called\b",
                    clause,
                )
                for clause in clauses
            )
        )
        structured_row_hits += int(
            any(
                re.search(rf"\b{escaped_term}\b[^.!?]{{0,160}}(?:\||->)", clause)
                and len(re.findall(r"[a-z0-9]+", clause)) >= 4
                for clause in clauses
            )
        )
    return min(2, relation_hits + called_hits + structured_row_hits)


def _obligation_term_stem(term: str) -> str:
    normalized = term.lower().strip(" _-")
    if len(normalized) > 4 and normalized.endswith("ies"):
        return f"{normalized[:-3]}y"
    if len(normalized) > 3 and normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def _verb_forms(verb: str) -> tuple[str, ...]:
    normalized = verb.lower().strip()
    nominal_forms = {
        "calculate": ("calculation", "calculations"),
        "classify": ("classification", "classifications"),
        "compute": ("computation", "computations"),
        "derive": ("derivation", "derivations"),
        "encode": ("encoding", "encodings"),
        "identify": ("identification", "identifications"),
        "interpret": ("interpretation", "interpretations"),
        "optimize": ("optimization", "optimizations"),
        "predict": ("prediction", "predictions"),
        "represent": (
            "representation", "representations", "encode", "encodes",
            "encoded", "encoding", "encodings",
        ),
        "transform": ("transformation", "transformations"),
    }
    if normalized.endswith("y") and len(normalized) > 2:
        forms = (
            normalized,
            f"{normalized[:-1]}ies",
            f"{normalized[:-1]}ied",
            f"{normalized}ing",
        )
    elif normalized.endswith("e"):
        forms = (normalized, f"{normalized}s", f"{normalized}d", f"{normalized[:-1]}ing")
    else:
        forms = (normalized, f"{normalized}s", f"{normalized}ed", f"{normalized}ing")
    return tuple(dict.fromkeys((*forms, *nominal_forms.get(normalized, ()))))


def _comparison_sides(query: str) -> tuple[str, str] | None:
    normalized = re.sub(r"\s+", " ", query.strip().lower()).strip(" ?.!")
    match = re.match(
        r"^(?:compare|contrast)\s+(.+?)\s+(?:and|versus|vs\.?)\s+"
        r"(.+?)(?:\s+(?:for|in|on|during|within)\b.*|$)",
        normalized,
    )
    if not match:
        match = re.match(
            r"^(?:what\s+is\s+)?(?:the\s+)?difference\s+between\s+(.+?)\s+and\s+(.+)$",
            normalized,
        )
    if not match:
        return None
    first = re.sub(r"^(?:a|an|the)\s+", "", match.group(1)).strip()
    second = re.sub(r"^(?:a|an|the)\s+", "", match.group(2)).strip()
    axis_prefix = (
        r"^(?:actions?|behaviou?r|effects?|outcomes?|results?|responses?|requirements?|"
        r"recommendations?|steps?|procedures?)\s+(?:for|of|under|with)\s+"
    )
    first = re.sub(axis_prefix, "", first).strip()
    second = re.sub(axis_prefix, "", second).strip()
    first_words = first.split()
    second_words = second.split()
    if len(first_words) == 1 and len(second_words) >= 2:
        first = " ".join((first_words[0], *second_words[1:]))
    if not first or not second:
        return None
    return first, second


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
        "works well",
        "works as",
        "works when",
        "operates by",
        "consists of",
        "composed of",
        "because ",
        "so that",
        "the pattern",
        "the flow",
        "only when",
        "for each",
        " then ",
        "compute ",
        "applies ",
        "apply ",
        "computes ",
        "calculates ",
        "calculate ",
        "calculated as",
        "computed as",
        "given by",
        " equals ",
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
    "workflow_placement": (
        "workflow ",
        "stage ",
        "step ",
        " selecting ",
        " evaluated ",
        " tuning ",
        " before ",
        " after ",
        " during ",
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
        "avoid ",
        "rather than",
        "should not",
        "must not",
        "not suitable",
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
    object_focus_match = re.match(
        r"^(?:how|why)\s+(?:does|do)\s+.+?\s+"
        r"(?:use|uses|employ|employs|apply|applies|represent|represents)\s+"
        r"(.+?)(?:\?|$)",
        normalized,
        flags=re.I,
    )
    document_actor_match = re.match(
        r"^(?:how|why)\s+(?:does|do)\s+(?:the\s+)?"
        r"(?:book|document|module|paper|source|textbook)\s+"
        r"(?:describe|place|explain|present|define|recommend|mention|position|fit|integrate|relate|connect)"
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
        object_focus_match.group(1)
        if object_focus_match
        else document_actor_match.group(1)
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
    obligations = _evidence_obligations(
        answer_type=answer_type,
        query=normalized,
        requested=requested,
    )
    return AnswerPlan(
        answer_type=answer_type,
        subject=subject,
        depth=depth,
        sections=sections,
        requested_elements=requested,
        evidence_obligations=obligations,
    )


def _answer_type(query: str, mode: str) -> str:
    if mode in {"paper", "research_paper"} and re.search(
        r"\b(?:draft|write|compose|paper\s+section|research\s+paper|related\s+work|methodology|abstract)\b",
        query,
    ):
        return "academic_draft"
    if mode in {"exam", "exam_answer", "revision_notes", "important_questions", "study_guide"}:
        return "exam_response"
    if _is_document_summary_task(query=query, mode=mode):
        return "document_summary"
    if mode == "compare_concepts" or re.search(
        r"\b(compare|compared|contrast|difference|differences|versus|vs\.?|distinguish)\b",
        query,
    ):
        return "comparison"
    if re.search(
        r"\bwhen\s+should\b.{0,120}\b(?:avoid|abstain|refuse|decline|not\s+answer|say|prefer)\b",
        query,
    ):
        return "recommendation"
    if re.search(r"\b(?:recommend|recommends|recommended|recommendation|recommendations)\b", query):
        return "recommendation"
    if re.search(
        r"\b(?:book|document|module|paper|source|textbook)\b.{0,64}"
        r"\b(?:place|places|position|positions|fit|fits|integrate|integrates|relate|relates|"
        r"connect|connects|describe|describes|outline|outlines)\b"
        r".{0,72}\bworkflow\b",
        query,
    ):
        return "workflow_placement"
    if re.search(
        r"\b(?:how\s+to|steps?|procedure|pipeline|process\s+for|workflow\s+(?:for|of)|"
        r"(?:outline|describe)\b.{0,40}\bworkflow)\b",
        query,
    ):
        return "procedure"
    if re.search(r"\b(limitations?|drawbacks?|disadvantages?|failure\s+cases?|caveats?)\b", query):
        return "limitations"
    if re.search(
        r"\b(?:what|which)\b.{0,100}\bshould\b.{0,100}\b(?:avoid|not|never|cannot|can't)\b",
        query,
    ):
        return "limitations"
    if re.search(
        r"\b(?:what|which)\b.{0,100}\b(?:must\s+not|should\s+not|cannot|can't)\b"
        r"|\b(?:what|which)\b.{0,100}\bmust\b.{0,100}\bnot\b",
        query,
    ):
        return "limitations"
    if re.search(
        r"\b(?:what|which)\b.{0,100}\bshould\b.{0,100}\b"
        r"(?:include|communicate|contain|show|use|choose|select|prioritize)\b",
        query,
    ):
        return "recommendation"
    if re.search(r"\b(interpret|interprets|interpreted|interpretation|what\s+does\b.+\bmean)\b", query):
        return "interpretation"
    if re.search(
        r"\b(when|who|how\s+many|what\s+year|which\s+year|release\s+date|which\s+edition|"
        r"hardware|training\s+duration)\b",
        query,
    ):
        return "factual_lookup"
    if re.match(
        r"^what\s+are\s+(?:the\s+)?(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+",
        query,
    ):
        return "enumeration"
    if re.search(r"\b(list|name|types?|kinds?|examples?|which)\b", query):
        return "enumeration"
    if re.match(r"^(?:what\s+(?:is|are)|define)\b", query):
        return "concept_explanation"
    if re.search(
        r"\b(how\s+does|how\s+do|how\s+is|how\s+should|why\s+does|why\s+do|working|mechanism|"
        r"what\s+does\b.{0,60}\b(?:consist\s+of|contain|transform))\b",
        query,
    ):
        return "mechanism_explanation"
    if re.search(r"\b(what\s+is|what\s+are|define|explain|describe|tell\s+me\s+about)\b", query):
        return "concept_explanation"
    if mode == "deep_research":
        return "deep_analysis"
    return "direct_answer"


def _is_document_summary_task(*, query: str, mode: str) -> bool:
    """Distinguish a summary command from references to an existing overview."""

    if re.search(r"\bsummarize\b", query):
        return True
    if re.search(
        r"^(?:please\s+)?(?:give|provide|create|write|make)?\s*(?:a\s+|an\s+|the\s+)?"
        r"(?:summary|overview|abstract)\b",
        query,
    ):
        return True
    if re.search(r"\b(?:summary|overview|abstract)\s+of\b", query):
        return True
    if mode != "summary":
        return False
    specific_task_terms = {
        "compare",
        "contrast",
        "define",
        "difference",
        "explain",
        "how",
        "list",
        "name",
        "which",
        "why",
    }
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", query))
    return not bool(tokens & specific_task_terms)


def _evidence_obligations(
    *,
    answer_type: str,
    query: str,
    requested: tuple[str, ...],
) -> tuple[EvidenceObligation, ...]:
    identity = EvidenceObligation(
        key="identity",
        label="definition or identity",
        retrieval_terms=("definition", "meaning", "concept"),
        evidence_cues=(" is a ", " is an ", " refers to ", " means ", " defined as ", " called "),
    )
    operation = EvidenceObligation(
        key="operation",
        label="core operation",
        retrieval_terms=(
            "process", "operation", "compute", "calculate", "derive", "apply", "transform", "divide",
            "combine", "drop", "ignore", "active",
        ),
        evidence_cues=(
            " works by ", " compute ", " computes ", " computed ", " calculated as ",
            " computed as ", " derived as ", " given by ", " equals ", " apply ",
            " applies ", " applied ", " transform ", " transforms ", " transforming ",
            " divide ", " divides ", " combine ", " combines ",
            " refines ", " refining ", " process ", " processes ", " processing ",
            " add ", " adds ", " added ", " inject ", " injects ",
            " counts ", " connects ", " selects ", " updates ", " consists of ",
            " composed of ", " linear transformation", " for each ",
            " uses ", " employs ", " masks ", " masking ", " sets ",
            " drops ", " dropped ", " ignored ", " active ",
            " increases ", " increasing ", " decreases ", " decreasing ",
            " prevents ", " prevent ", " ensures ", " ensure ",
            " works ", " because ", " pattern ", " flow ", " only when ",
        ),
    )
    result = EvidenceObligation(
        key="result",
        label="result or effect",
        retrieval_terms=("result", "output", "effect", "produce", "form"),
        evidence_cues=(
            " produces ", " results in ", " so that ", " forms ", " output ",
            " identified as ", " represented ", " reduce ", " prevents ", " labels ",
            " into ", " yields ", " generates ", " creates ", " updates ", " reduces ",
            " considered ", " classified as ",
        ),
    )

    if answer_type == "document_summary":
        return (
            EvidenceObligation(
                key="scope",
                label="document scope",
                retrieval_terms=("chapter", "section", "part", "covers", "overview"),
                evidence_cues=(" covers ", " chapter ", " part i ", " part ii ", " overview "),
            ),
            EvidenceObligation(
                key="representative_points",
                label="representative main points",
                retrieval_terms=("main", "method", "finding", "conclusion", "limitation"),
                evidence_cues=(" main ", " method ", " result ", " conclusion ", " limitation "),
            ),
        )
    if answer_type == "enumeration":
        return (
            EvidenceObligation(
                key="items",
                label="requested items",
                retrieval_terms=(
                    "list", "listed", "includes", "common", "types", "methods",
                    "algorithms", "components", "layers", "first", "second",
                ),
                evidence_cues=(
                    " includes ", " include ", " listed ", " following ", " common ",
                    " types of ", " methods ", " algorithms ", " consists of ",
                    " sub-layers ", " components ", " first ", " second ", " each ",
                ),
            ),
            EvidenceObligation(
                key="scope",
                label="requested scope",
                retrieval_terms=("scope", "chapter", "part", "section", "overview"),
                evidence_cues=(" chapter ", " part i ", " part ii ", " section ", " overview ", " covers "),
                required=False,
            ),
        )
    if answer_type == "workflow_placement":
        return (
            EvidenceObligation(
                key="placement",
                label="workflow placement",
                retrieval_terms=("workflow", "stage", "step", "before", "after", "during"),
                evidence_cues=(
                    " before ", " after ", " during ", " when ", " stage ",
                    " step ", " workflow ", " selecting ",
                ),
            ),
            EvidenceObligation(
                key="workflow_action",
                label="action performed at that stage",
                retrieval_terms=("select", "evaluate", "tune", "apply", "use"),
                evidence_cues=(" selecting ", " evaluate ", " evaluated ", " tuning ", " tune ", " using ", " used to "),
            ),
        )
    if answer_type == "factual_lookup":
        subject_terms = tuple(
            token
            for token in re.findall(r"[a-z][a-z0-9_-]{2,}", _subject(query))
            if token not in {"the", "this", "that"}
        )
        query_terms = tuple(
            token
            for token in re.findall(r"[a-z][a-z0-9_-]{2,}", query)
            if token not in {
                "what", "which", "when", "where", "who", "are", "is", "was", "were",
                "the", "a", "an", "and", "for", "from", "reported", "shown", "listed",
                "given", "recorded", "displayed", "published",
            }
        )
        retrieval_terms = tuple(dict.fromkeys((*subject_terms, *query_terms)))[:14]
        return (
            EvidenceObligation(
                key="requested_facts",
                label="requested factual details",
                retrieval_terms=retrieval_terms or ("fact", "details"),
                evidence_cues=(
                    " reported ", " shown ", " listed ", " given ", " recorded ",
                    " published ", " released ", " edition ", " date ", " duration ",
                    " hardware ", " gpu", " machine ", " steps ", " hours ",
                ),
                required=False,
            ),
        )
    if answer_type == "mechanism_explanation":
        obligations: list[EvidenceObligation] = []
        if re.search(r"\bwhy\b", query):
            obligations.append(
                EvidenceObligation(
                    key="rationale",
                    label="reason or intended effect",
                    retrieval_terms=(
                        "reason", "purpose", "allow", "enable", "avoid", "reduce",
                        "fight", "combat", "curse",
                    ),
                    evidence_cues=(
                        " because ", " in order to ", " so that ", " allows ", " allow ",
                        " enables ", " enable ", " prevents ", " prevent ", " ensures ",
                        " ensure ", " depends only ", " depend only ", " reduces ",
                        " reduce ", " counteract ", " to fight ", " to combat ",
                        " purpose ", " reason ",
                    ),
                )
            )
        focus_match = re.search(
            r"\b(comput(?:e|es|ed|ing)|calculat(?:e|es|ed|ing)|deriv(?:e|es|ed|ing)|"
            r"identify|mask|update|transform|represent|encode|detect|classify|predict|"
            r"optimize|train|perform|fit)\b",
            query,
        )
        if focus_match:
            focus_verb = focus_match.group(1)
            if focus_verb.startswith("comput"):
                focus_verb = "compute"
            elif focus_verb.startswith("calculat"):
                focus_verb = "calculate"
            elif focus_verb.startswith("deriv"):
                focus_verb = "derive"
            focus_forms = _verb_forms(focus_verb)
            operation_tail_match = re.search(
                r"\b(?:perform|performs|performed|performing|apply|applies|applied|"
                r"use|uses|used|employ|employs|employed)\s+(.+?)(?:\?|$)",
                query,
            )
            if operation_tail_match:
                tail_terms = tuple(
                    token
                    for token in re.findall(r"[a-z][a-z0-9_-]{2,}", operation_tail_match.group(1))
                    if token not in {"the", "a", "an", "to", "on", "in", "for", "and"}
                )
                focus_forms = tuple(dict.fromkeys((*focus_forms, *tail_terms)))
            obligations.append(
                EvidenceObligation(
                    key="operation_focus",
                    label=f"requested {focus_verb} operation",
                    retrieval_terms=focus_forms,
                    evidence_cues=tuple(f" {form} " for form in focus_forms),
                )
            )
        if re.search(r"\b(create|creates|generate|generates|from|start|starts|input)\b", query):
            obligations.append(
                EvidenceObligation(
                    key="initial_state",
                    label="initial state or input",
                    retrieval_terms=("start", "initial", "input", "begin"),
                    evidence_cues=(
                        " starts with ", " start with ", " starting with ",
                        " begins with ", " beginning with ", " initial ",
                        " input ", " for each ",
                    ),
                )
            )
        obligations.append(
            operation
            if not focus_match and not re.search(r"\bwhy\b", query)
            else EvidenceObligation(
                key=operation.key,
                label=operation.label,
                retrieval_terms=operation.retrieval_terms,
                evidence_cues=operation.evidence_cues,
                required=False,
            )
        )
        target_match = re.search(
            r"\b(?:identify|identifies|detect|detects|label|labels|classify|classifies|find|finds)\s+"
            r"(?:the\s+)?([a-z][a-z0-9_-]*(?:\s+[a-z][a-z0-9_-]*){0,2})\s+and\s+"
            r"([a-z][a-z0-9_-]*(?:\s+[a-z][a-z0-9_-]*){0,2})(?:\?|$)",
            query,
        )
        if target_match:
            obligations = [
                item for item in obligations if item.key != "operation_focus"
            ]
            obligations.append(
                EvidenceObligation(
                    key="decision_condition",
                    label="decision condition or threshold",
                    retrieval_terms=("condition", "threshold", "minimum", "neighborhood", "core"),
                    evidence_cues=(" if ", " when ", " at least ", " then ", " requires "),
                )
            )
            for index, target in enumerate(target_match.groups(), start=1):
                target_terms = tuple(
                    token
                    for token in re.findall(r"[a-z][a-z0-9_-]{2,}", target)
                )
                obligations.append(
                    EvidenceObligation(
                        key=f"result_target_{index}",
                        label=f"result for {target}",
                        retrieval_terms=target_terms or (target,),
                        evidence_cues=result.evidence_cues,
                    )
                )
        elif re.search(
            r"\b(result|output|effect|produce|produces|form|forms|create|creates|"
            r"generate|generates|identify|identifies|detect|detects|label|labels|yield|yields|"
            r"update|updates|regularize|regularizes|reduce|reduces|prevent|prevents|"
            r"perform|performs|classify|classifies|predict|predicts)\b",
            query,
        ):
            obligations.append(result)
        if re.search(r"\b(each|separately|identically|component|components|consist|contain)\b", query):
            obligations.append(
                EvidenceObligation(
                    key="scope",
                    label="where the operation is applied",
                    retrieval_terms=("each", "scope", "separately", "identically"),
                    evidence_cues=(" each ", " separately ", " identically ", " per "),
                )
            )
        return tuple(obligations[:4])
    if answer_type == "procedure":
        return (
            EvidenceObligation(
                key="ordered_steps",
                label="ordered steps",
                retrieval_terms=("first", "then", "next", "step", "procedure"),
                evidence_cues=(" first ", " then ", " next ", " finally ", " step ", " followed by "),
            ),
            result,
        )
    if answer_type == "comparison":
        comparison_sides = _comparison_sides(query)
        if comparison_sides:
            side_token_sets = [
                tuple(re.findall(r"[a-z][a-z0-9_-]{2,}", side))
                for side in comparison_sides
            ]
            shared_side_terms = set.intersection(
                *(set(tokens) for tokens in side_token_sets)
            ) if len(side_token_sets) > 1 else set()
            side_obligations = tuple(
                EvidenceObligation(
                    key=f"comparison_side_{index}",
                    label=f"evidence for {side}",
                    retrieval_terms=(
                        tuple(token for token in side_token_sets[index - 1] if token not in shared_side_terms)
                        or side_token_sets[index - 1]
                    ),
                    evidence_cues=(
                        " is a ", " is an ", " is called ", " called ", " measures ",
                        " ratio ", " fraction ", " means ", " refers to ",
                        " adapts ", " adapt ", " learns ", " learn ", " sensitive ",
                        " causes ", " makes ",
                    ),
                )
                for index, side in enumerate(comparison_sides, start=1)
            )
            return (
                *side_obligations,
                EvidenceObligation(
                    key="contrast",
                    label="direct contrast",
                    retrieval_terms=("whereas", "difference", "compared", "while", "unlike"),
                    evidence_cues=(
                        " whereas ", " while ", " unlike ", " compared to ",
                        " difference ", " in contrast ",
                    ),
                    required=False,
                ),
            )
        return (
            EvidenceObligation(
                key="contrast",
                label="direct contrast",
                retrieval_terms=("whereas", "difference", "compared", "while", "unlike"),
                evidence_cues=(
                    " whereas ", " while ", " unlike ", " compared to ", " difference ",
                    " in contrast ", " high ", " low ", " higher ", " lower ",
                    " faster ", " slower ", " more ", " less ",
                ),
            ),
            EvidenceObligation(
                key="comparison_axis",
                label="shared comparison axis",
                retrieval_terms=("measure", "purpose", "use", "ratio", "metric"),
                evidence_cues=(" measures ", " ratio of ", " used to ", " indicates ", " metric "),
            ),
        )
    if answer_type == "concept_explanation":
        obligations = [identity]
        if re.search(r"\bwhy\b", query):
            obligations.extend(
                (
                    EvidenceObligation(
                        key="operating_condition",
                        label="operating condition",
                        retrieval_terms=("when", "condition", "before", "after", "stop"),
                        evidence_cues=(" when ", " before ", " after ", " until ", " minimum ", " best ", " stop ", " interrupt "),
                    ),
                    EvidenceObligation(
                        key="rationale",
                        label="reason or benefit",
                        retrieval_terms=("why", "reason", "purpose", "avoid", "prevent", "reduce"),
                        evidence_cues=(" because ", " to avoid ", " prevents ", " reduce ", " so that ", " purpose ", " reason "),
                    ),
                )
            )
        else:
            obligations.append(
                EvidenceObligation(
                    key=operation.key,
                    label=operation.label,
                    retrieval_terms=operation.retrieval_terms,
                    evidence_cues=operation.evidence_cues,
                    required=False,
                )
            )
            obligations.append(
                EvidenceObligation(
                    key="structure",
                    label="main components or building blocks",
                    retrieval_terms=("component", "components", "building", "block", "layer", "layers"),
                    evidence_cues=(
                        " building block ", " consists of ", " composed of ",
                        " component ", " components ", " layer ", " layers ",
                    ),
                    required=False,
                )
            )
        return tuple(obligations[:4])
    if answer_type == "limitations":
        obligations: list[EvidenceObligation] = []
        if "benefits" in requested:
            obligations.append(
                EvidenceObligation(
                    key="benefit",
                    label="benefit or advantage",
                    retrieval_terms=("benefit", "advantage", "improve", "faster", "reduce"),
                    evidence_cues=(
                        " benefit ", " advantage ", " improves ", " improve ", " faster ",
                        " speeding up ", " speeds up ", " reduces ", " reduce ",
                        " regularizer ", " less sensitive ", " allows ",
                    ),
                )
            )
        obligations.append(
            EvidenceObligation(
                key="limitation",
                label="limitation or runtime cost",
                retrieval_terms=("limitation", "drawback", "penalty", "overhead", "runtime", "slower"),
                evidence_cues=(
                    " limitation ", " drawback ", " however ", " penalty ", " overhead ",
                    " runtime ", " slower ", " slows ", " complexity ", " expensive ",
                    " cannot ", " does not ", " risk ",
                ),
            )
        )
        return tuple(obligations)
    if answer_type == "recommendation":
        return (
            EvidenceObligation(
                key="recommended_action",
                label="recommended action",
                retrieval_terms=("recommend", "should", "use", "verify", "check", "validate"),
                evidence_cues=(
                    " recommend ", " recommends ", " should ", " use ", " verify ",
                    " validate ", " cross-check ", " cross check ", " avoid ", " return ",
                ),
            ),
            EvidenceObligation(
                key="fallback_condition",
                label="condition or fallback",
                retrieval_terms=("if", "when", "fallback", "uncertain"),
                evidence_cues=(" if ", " when ", " fallback ", " uncertain ", " uncertainty "),
                required=False,
            ),
        )
    if answer_type == "interpretation":
        return (
            EvidenceObligation(
                key="value_mapping",
                label="value-to-outcome mapping",
                retrieval_terms=("value", "positive", "negative", "zero", "high", "low", "boundary"),
                evidence_cues=(
                    " close to ", " means that ", " indicates that ", " positive ",
                    " negative ", " boundary ", " well inside ", " far from ",
                ),
                required=False,
            ),
            EvidenceObligation(
                key="interpretive_relation",
                label="meaning or interpretation",
                retrieval_terms=("mean", "indicate", "represent", "interpret", "close", "range"),
                evidence_cues=(
                    " means ", " indicates ", " represents ", " interpreted as ",
                    " close to ", " ranges from ", " can vary between ",
                ),
            ),
        )
    return (identity,)


def _answer_depth(
    query: str,
    mode: str,
    exam_profile: dict[str, object] | None,
) -> str:
    if re.search(r"\b(brief|briefly|concise|short|in\s+one\s+sentence)\b", query):
        return "brief"
    if mode in {"deep_research", "paper", "research_paper", "study_guide"} or re.search(
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
        ("steps", r"\b(?:step|steps|procedure|pipeline|how\s+to|workflow\s+(?:for|of))\b"),
        (
            "diagram references",
            r"(?:\b(?:provide|include|show|with|add|cite)\s+(?:an?\s+)?"
            r"(?:image|images|diagram|diagrams|figure|figures|visuals?)\b|"
            r"\b(?:image|diagram|figure|visual)\s+references?\b)",
        ),
        (
            "equations",
            r"\b(equation|equations|formula|formulas|derive|derivation)\b|"
            r"\bhow\s+(?:is|are)\b.{0,80}\b(?:calculated|computed|derived)\b",
        ),
        ("comparison", r"\b(compare|contrast|difference|differences|versus|vs\.?)\b"),
    )
    for label, pattern in patterns:
        if re.search(pattern, query):
            requested.append(label)
    return tuple(requested)


def _subject(query: str) -> str:
    subject = re.sub(r"\s+", " ", query.strip()).strip(" ?.!")
    comparison_sides = _comparison_sides(subject)
    if comparison_sides:
        return " and ".join(comparison_sides)
    owner_subject_match = re.match(
        r"^what\s+.+?\s+does\s+(.+?)\s+"
        r"(?:have|provide|offer|cause|add|require)$",
        subject,
        flags=re.I,
    )
    object_focus_match = re.match(
        r"^(?:how|why)\s+(?:does|do)\s+.+?\s+"
        r"(?:use|uses|employ|employs|apply|applies|represent|represents)\s+(.+)$",
        subject,
        flags=re.I,
    )
    recommendation_subject_match = re.match(
        r"^what\s+does\s+.+?\b(?:book|document|module|paper|source|textbook)\s+"
        r"recommend(?:s|ed|ing)?(?:\s+(?:for|about|when))?\s+(.+)$",
        subject,
        flags=re.I,
    )
    topic_scope_match = re.match(
        r"^(?:which|what)\s+topics?\s+(?:does|do)\s+(.+?)\s+"
        r"(?:cover|covers|include|includes|list|lists)$",
        subject,
        flags=re.I,
    )
    listed_subject_match = re.match(
        r"^(?:which|what)\s+(.+?)\s+(?:are|is)\s+"
        r"(?:listed|included|covered|mentioned)\b",
        subject,
        flags=re.I,
    )
    focus_tail_match = re.match(
        r"^(?:what|which)\s+.+?\s+(?:behind|reported\s+for|shown\s+for|"
        r"given\s+for|recorded\s+for)\s+(?:the\s+)?(.+)$",
        subject,
        flags=re.I,
    )
    should_include_match = re.match(
        r"^what\s+(.+?)\s+should\s+.+?\s+(?:include|mention|contain|show)$",
        subject,
        flags=re.I,
    )
    leading_should_action_match = re.match(
        r"^what\s+should\s+(.+?)\s+"
        r"(?:avoid|not|never|cannot|can't|include|communicate|contain|show|"
        r"use|choose|select|prioritize)(?:\s+.+)?$",
        subject,
        flags=re.I,
    )
    should_action_match = re.match(
        r"^(?:what|which)\s+(.+?)\s+should\s+.+?\s+"
        r"(?:avoid|not|never|cannot|can't|include|communicate|contain|show|"
        r"use|choose|select|prioritize)(?:\s+.+)?$",
        subject,
        flags=re.I,
    )
    if recommendation_subject_match:
        subject = recommendation_subject_match.group(1).strip()
    elif owner_subject_match:
        subject = owner_subject_match.group(1).strip()
    elif object_focus_match:
        subject = object_focus_match.group(1).strip()
    elif topic_scope_match:
        subject = topic_scope_match.group(1).strip()
    elif listed_subject_match:
        subject = listed_subject_match.group(1).strip()
    elif focus_tail_match:
        subject = focus_tail_match.group(1).strip()
    elif should_include_match:
        subject = should_include_match.group(1).strip()
    elif leading_should_action_match:
        subject = leading_should_action_match.group(1).strip()
        subject = re.sub(r"\s+(?:of|for|in)\s+.+$", "", subject, flags=re.I).strip()
    elif should_action_match:
        subject = should_action_match.group(1).strip()
    else:
        subject = _LEADING_REQUEST.sub("", subject).strip()
    mechanism_subject_match = re.match(
        r"^(.+?)\s+(?:work|works|comput(?:e|es|ed|ing)|calculat(?:e|es|ed|ing)|"
        r"deriv(?:e|es|ed|ing)|represent|represents|identify|identifies|"
        r"regularize|regularizes|transform|transforms|update|updates|mask|masks|reduce|reduces|"
        r"use|uses|apply|applies|select|selects|detect|detects|generate|generates|create|creates|"
        r"classify|classifies|predict|predicts|train|trains|perform|performs|fit|fits)\b",
        subject,
        flags=re.I,
    )
    if mechanism_subject_match:
        subject = mechanism_subject_match.group(1).strip()
    subject = re.sub(
        r"^(?:the\s+)?(?:book|source|document|paper|textbook|module)\s+"
        r"(?:describe|describes|place|places|explain|explains|present|presents|define|defines|"
        r"recommend|recommends|mention|mentions)\s+",
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
    subject = re.sub(
        r"\s+(?:and\s+)?(?:how|why)\s+(?:does|do|is|are)\b.*$",
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
    elif answer_type == "workflow_placement":
        sections = ["Direct answer", "Where it fits", "What happens there"]
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
