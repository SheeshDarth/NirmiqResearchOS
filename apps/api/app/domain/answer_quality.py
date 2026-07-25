from collections.abc import Sequence
import re

from app.domain.answer_intelligence import build_answer_plan
from app.domain.citation_coverage import citation_coverage
from app.domain.text_normalization import normalize_token_text


_CONTENT_STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "action",
    "are",
    "as",
    "at",
    "be",
    "because",
    "before",
    "between",
    "book",
    "by",
    "can",
    "describe",
    "does",
    "document",
    "expected",
    "explain",
    "for",
    "from",
    "include",
    "includes",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "model",
    "mention",
    "mentioned",
    "of",
    "on",
    "or",
    "paper",
    "reported",
    "source",
    "shown",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "what",
    "when",
    "which",
    "why",
    "with",
    "listed",
    "provided",
    "recommended",
    "recommends",
    "structure",
}

_STRUCTURAL_HEADINGS = {
    "applications",
    "conclusion",
    "direct answer",
    "direct comparison",
    "equation or reason from the source",
    "equations",
    "evidence",
    "evidence note",
    "exam-ready answer",
    "examples",
    "explanation",
    "finding",
    "goal",
    "how it works",
    "important questions",
    "key differences",
    "key points",
    "limitations",
    "main ideas",
    "overview",
    "practical takeaway",
    "short answer",
    "source diagram references",
    "source note",
    "steps",
    "steps from the source",
    "what it is used for",
    "why it matters",
}

_ABSTENTION_PHRASES = (
    "does not contain enough",
    "do not have enough",
    "insufficient evidence",
    "not enough direct evidence",
    "more context",
    "more evidence",
    "not found in",
    "not in the source",
    "not supported by",
    "unable to answer from",
    "could not find this in",
)


def evaluate_answer_quality(
    *,
    query: str,
    answer: str,
    grounded: bool,
    retrieval_meta: dict[str, object] | None,
    response_mode: str = "research",
    answerability: str = "answerable",
    expected_answer: str | None = None,
    required_concepts: Sequence[Sequence[str]] | None = None,
) -> dict[str, object]:
    """Score answer behavior with deterministic, local, auditable checks.

    These scores are evaluation diagnostics, not a semantic truth oracle. Human-
    reviewed concepts and source evidence remain the benchmark ground truth.
    """

    normalized_answerability = _normalize_answerability(answerability)
    meta = retrieval_meta or {}
    answerability_score = _answerability_score(
        answer=answer,
        grounded=grounded,
        answerability=normalized_answerability,
    )
    concept_score, concept_hits, concept_total = _concept_coverage(
        answer=answer,
        expected_answer=expected_answer,
        required_concepts=required_concepts,
        answerability=normalized_answerability,
        answerability_score=answerability_score,
    )
    query_focus_score = _query_focus_score(
        query=query,
        answer=answer,
        answerability=normalized_answerability,
        answerability_score=answerability_score,
    )
    plan_score, plan_checks = _plan_compliance(
        query=query,
        answer=answer,
        response_mode=response_mode,
        answerability=normalized_answerability,
    )
    readability_score, readability_issues = _readability(answer)
    faithfulness_score, faithfulness_checks = _faithfulness(
        answer=answer,
        grounded=grounded,
        retrieval_meta=meta,
        answerability=normalized_answerability,
    )
    answer_relevance_score = round((concept_score * 0.7) + (query_focus_score * 0.3), 3)

    if normalized_answerability == "unanswerable":
        overall_score = round(
            (answerability_score * 0.5)
            + (faithfulness_score * 0.3)
            + (readability_score * 0.2),
            3,
        )
    else:
        overall_score = round(
            (answer_relevance_score * 0.35)
            + (plan_score * 0.15)
            + (readability_score * 0.2)
            + (faithfulness_score * 0.3),
            3,
        )

    failure_reasons: list[str] = []
    if answerability_score < 1.0:
        failure_reasons.append("answerability_mismatch")
    if normalized_answerability != "unanswerable" and answer_relevance_score < 0.55:
        failure_reasons.append("low_answer_relevance")
    if plan_score < 0.6:
        failure_reasons.append("query_plan_not_fulfilled")
    if readability_score < 0.7:
        failure_reasons.append("poor_readability")
    if faithfulness_score < 0.75:
        failure_reasons.append("weak_claim_support")

    return {
        "passed": not failure_reasons,
        "overall_score": overall_score,
        "answer_relevance": answer_relevance_score,
        "concept_coverage": concept_score,
        "query_focus": query_focus_score,
        "plan_compliance": plan_score,
        "readability": readability_score,
        "faithfulness": faithfulness_score,
        "answerability_correct": answerability_score,
        "answerability": normalized_answerability,
        "concept_hits": concept_hits,
        "concept_total": concept_total,
        "plan_checks": plan_checks,
        "readability_issues": readability_issues,
        "faithfulness_checks": faithfulness_checks,
        "failure_reasons": failure_reasons,
    }


def _normalize_answerability(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"unanswerable", "partial", "answerable"}:
        return normalized
    return "answerable"


def _answerability_score(*, answer: str, grounded: bool, answerability: str) -> float:
    normalized_answer = normalize_token_text(answer)
    abstains = any(phrase in normalized_answer for phrase in _ABSTENTION_PHRASES)
    if answerability == "unanswerable":
        return 1.0 if not grounded and abstains else 0.0
    if answerability == "partial":
        return 1.0 if (not grounded or abstains or "not available" in normalized_answer) else 0.5
    return 1.0 if grounded and len(_content_terms(answer)) >= 3 else 0.0


def _concept_coverage(
    *,
    answer: str,
    expected_answer: str | None,
    required_concepts: Sequence[Sequence[str]] | None,
    answerability: str,
    answerability_score: float,
) -> tuple[float, int, int]:
    if answerability == "unanswerable":
        return answerability_score, int(answerability_score == 1.0), 1

    normalized_answer = normalize_token_text(answer)
    concept_groups = [
        [normalize_token_text(alias) for alias in group if normalize_token_text(alias)]
        for group in (required_concepts or [])
        if group
    ]
    if concept_groups:
        hits = sum(
            1
            for aliases in concept_groups
            if any(alias in normalized_answer for alias in aliases)
        )
        return round(hits / len(concept_groups), 3), hits, len(concept_groups)

    expected_terms = _content_terms(expected_answer or "")
    if not expected_terms:
        return 1.0, 0, 0
    answer_terms = _content_terms(answer)
    hits = sum(1 for term in expected_terms if _term_present(term, answer_terms))
    return round(hits / len(expected_terms), 3), hits, len(expected_terms)


def _query_focus_score(
    *,
    query: str,
    answer: str,
    answerability: str,
    answerability_score: float,
) -> float:
    if answerability == "unanswerable":
        return answerability_score
    plan = build_answer_plan(query=query, response_mode="research")
    subject_terms = _content_terms(plan.subject)
    if not subject_terms:
        return 1.0
    answer_terms = _content_terms(answer)
    hits = sum(1 for term in subject_terms if _term_present(term, answer_terms))
    return round(hits / len(subject_terms), 3)


def _plan_compliance(
    *,
    query: str,
    answer: str,
    response_mode: str,
    answerability: str,
) -> tuple[float, dict[str, bool]]:
    if answerability == "unanswerable":
        return 1.0, {"abstention_is_the_plan": True}

    plan = build_answer_plan(query=query, response_mode=response_mode)
    normalized = normalize_token_text(answer)
    bullet_count = sum(
        1 for line in answer.splitlines() if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
    )
    checks: dict[str, bool] = {}
    if plan.answer_type == "comparison":
        checks["comparison_language"] = bool(
            re.search(
                r"\b(?:whereas|while|compared|comparison|differences?|both|unlike|versus|vs)\b",
                normalized,
            )
        )
    elif plan.answer_type == "procedure":
        checks["ordered_process"] = bullet_count >= 2 or bool(
            re.search(r"\b(?:first|then|next|finally|step|pipeline)\b", normalized)
        )
    elif plan.answer_type == "limitations":
        checks["limitations_addressed"] = bool(
            re.search(r"\b(?:limitation|drawback|caveat|struggle|however)\b", normalized)
        )
    elif plan.answer_type == "enumeration":
        checks["multiple_items"] = bullet_count >= 2
    else:
        checks["direct_explanation"] = len(_content_terms(answer)) >= 5

    requested_checks = {
        "examples": r"\bexamples?\b",
        "applications": r"\b(?:applications?|used for|use cases?)\b",
        "limitations": r"\b(?:limitations?|drawbacks?|caveats?|not available)\b",
        "steps": r"\b(?:steps?|first|then|next|finally|pipeline)\b",
        "diagram references": r"\b(?:images?|diagrams?|figures?|visual|not available)\b",
        "equations": r"\b(?:equations?|formulas?|derivation)\b|=",
        "comparison": r"\b(?:whereas|while|comparison|differences?|both|unlike|versus|vs)\b",
    }
    for element in plan.requested_elements:
        pattern = requested_checks.get(element)
        if pattern:
            matched = bool(re.search(pattern, normalized))
            if element == "equations":
                matched = matched or bool(
                    re.search(r"\b[A-Za-z][A-Za-z0-9_]*\s*=\s*\S+", answer)
                ) or " equals " in normalized
            checks[f"requested_{element.replace(' ', '_')}"] = matched

    if plan.depth == "detailed":
        checks["requested_depth"] = len(answer.split()) >= 45
    elif plan.depth == "brief":
        checks["requested_depth"] = len(answer.split()) <= 180

    score = sum(1 for value in checks.values() if value) / len(checks) if checks else 1.0
    return round(score, 3), checks


def _readability(answer: str) -> tuple[float, list[str]]:
    issues: list[str] = []
    normalized_lines: list[str] = []
    fragment_count = 0
    long_sentence_count = 0

    for raw_line in answer.splitlines():
        line = re.sub(r"^[#>*\s-]+", "", raw_line).strip()
        line_without_citations = re.sub(r"\[\d+\]", "", line).strip(" .:-")
        normalized = normalize_token_text(line_without_citations)
        if not normalized or normalized in _STRUCTURAL_HEADINGS:
            continue
        normalized_lines.append(normalized)
        words = line_without_citations.split()
        if re.fullmatch(r"(?:\[\d+\]\s*)+", line):
            fragment_count += 1
        elif len(words) < 3:
            fragment_count += 1
        elif re.search(r"\b(?:and|or|of|to|versus|vs|with)\.?$", normalized):
            fragment_count += 1

        for sentence in re.split(r"(?<=[.!?])\s+", line_without_citations):
            if len(sentence.split()) > 80:
                long_sentence_count += 1

    duplicate_count = len(normalized_lines) - len(set(normalized_lines))
    if fragment_count:
        issues.append(f"fragments:{fragment_count}")
    if duplicate_count:
        issues.append(f"duplicate_lines:{duplicate_count}")
    if long_sentence_count:
        issues.append(f"long_sentences:{long_sentence_count}")
    if not normalized_lines:
        issues.append("no_readable_content")

    penalty = min(
        1.0,
        (fragment_count * 0.25)
        + (duplicate_count * 0.2)
        + (long_sentence_count * 0.1)
        + (0.75 if not normalized_lines else 0.0),
    )
    return round(1.0 - penalty, 3), issues


def _faithfulness(
    *,
    answer: str,
    grounded: bool,
    retrieval_meta: dict[str, object],
    answerability: str,
) -> tuple[float, dict[str, bool]]:
    if answerability == "unanswerable":
        checks = {
            "not_grounded": not grounded,
            "no_citation_anchors": not bool(re.search(r"\[\d+\]", answer)),
        }
        return round(sum(checks.values()) / len(checks), 3), checks

    coverage = retrieval_meta.get("citation_coverage")
    if not isinstance(coverage, (int, float)):
        coverage = citation_coverage(answer).get("citation_coverage", 0.0)
    unsupported = retrieval_meta.get("unsupported_claims")
    checks = {
        "grounded": grounded,
        "citations_present": bool(re.search(r"\[\d+\]", answer)),
        "citation_coverage": float(coverage or 0.0) >= 0.75,
        "verification_supported": retrieval_meta.get("citation_verification_state") == "supported",
        "no_unsupported_claims": not isinstance(unsupported, list) or not unsupported,
    }
    return round(sum(checks.values()) / len(checks), 3), checks


def _content_terms(value: str) -> set[str]:
    terms = set(normalize_token_text(value).split())
    return {
        term
        for term in terms
        if term not in _CONTENT_STOPWORDS
        and (len(term) >= 3 or term.isdigit())
    }


def _term_present(expected: str, actual_terms: set[str]) -> bool:
    if expected in actual_terms:
        return True
    if len(expected) < 6:
        return False
    prefix = expected[:5]
    return any(len(actual) >= 6 and actual[:5] == prefix for actual in actual_terms)
