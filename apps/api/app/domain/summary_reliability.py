from __future__ import annotations

from dataclasses import dataclass
import re
import time
import tracemalloc
from statistics import median
from typing import Any


SUMMARY_RELIABILITY_VERSION = "summary-reliability-v1"

_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "before",
    "between",
    "chapter",
    "document",
    "from",
    "have",
    "into",
    "more",
    "section",
    "that",
    "their",
    "these",
    "this",
    "through",
    "using",
    "which",
    "will",
    "with",
}


def validate_persisted_summary_meta(metadata: object) -> dict[str, object]:
    """Validate cache metadata before request-time fields are overlaid."""

    if not isinstance(metadata, dict):
        return {"valid": False, "issues": ["metadata_not_object"]}
    issues: list[str] = []
    if not isinstance(metadata.get("summary_profile"), str) or not metadata["summary_profile"]:
        issues.append("summary_profile_missing_or_invalid")
    if metadata.get("response_mode") != "summary":
        issues.append("response_mode_missing_or_invalid")
    if not isinstance(metadata.get("strategy"), str) or not metadata["strategy"]:
        issues.append("strategy_missing_or_invalid")
    hierarchy = metadata.get("summary_hierarchy")
    if not isinstance(hierarchy, dict):
        issues.append("summary_hierarchy_missing_or_invalid")
    else:
        if not isinstance(hierarchy.get("hierarchy_version"), str) or not hierarchy["hierarchy_version"]:
            issues.append("hierarchy_version_missing_or_invalid")
        if not isinstance(hierarchy.get("source_chunk_ids"), list) or not hierarchy["source_chunk_ids"]:
            issues.append("hierarchy_source_chunk_ids_missing_or_invalid")
    return {"valid": not issues, "issues": issues}


@dataclass(frozen=True)
class CitationSentenceAudit:
    sentence: str
    anchors: tuple[int, ...]
    support_score: float
    supported: bool


def audit_citation_support(
    answer: str,
    cited_rows: list[dict[str, Any]],
    *,
    minimum_support: float = 0.22,
) -> dict[str, object]:
    """Check that cited answer sentences have lexical support in cited excerpts.

    This is deliberately a conservative traceability check, not a semantic entailment
    model. It catches wrong citation wiring and index/noise leakage without adding a
    model dependency to the offline path.
    """

    rows_by_anchor: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(cited_rows, start=1):
        try:
            anchor = int(row.get("anchor") or index)
        except (TypeError, ValueError):
            anchor = index
        if anchor > 0:
            rows_by_anchor[anchor] = row

    audits: list[CitationSentenceAudit] = []
    invalid_anchor_count = 0
    for sentence in _claim_sentences(answer):
        anchors = tuple(int(value) for value in re.findall(r"\[(\d+)\]", sentence))
        if not anchors:
            audits.append(
                CitationSentenceAudit(
                    sentence=sentence,
                    anchors=(),
                    support_score=0.0,
                    supported=False,
                )
            )
            continue

        sentence_terms = _terms(sentence)
        scores: list[float] = []
        for anchor in anchors:
            row = rows_by_anchor.get(anchor)
            if row is None:
                invalid_anchor_count += 1
                continue
            source_text = str(row.get("text") or row.get("excerpt") or "")
            scores.append(_support_score(sentence_terms, _terms(source_text)))
        support_score = max(scores, default=0.0)
        threshold = minimum_support if len(sentence_terms) >= 6 else minimum_support * 0.65
        audits.append(
            CitationSentenceAudit(
                sentence=sentence,
                anchors=anchors,
                support_score=round(support_score, 3),
                supported=bool(scores) and support_score >= threshold,
            )
        )

    cited = [audit for audit in audits if audit.anchors]
    supported = [audit for audit in cited if audit.supported]
    support_coverage = round(len(supported) / len(cited), 3) if cited else 0.0
    return {
        "reliability_version": SUMMARY_RELIABILITY_VERSION,
        "sentence_count": len(audits),
        "cited_sentence_count": len(cited),
        "supported_sentence_count": len(supported),
        "citation_support_coverage": support_coverage,
        "invalid_anchor_count": invalid_anchor_count,
        "unsupported_citation_count": len(cited) - len(supported),
        "cache_safe": bool(
            cited
            and not invalid_anchor_count
            and len(supported) == len(cited)
        ),
        "sentences": [
            {
                "anchors": list(audit.anchors),
                "support_score": audit.support_score,
                "supported": audit.supported,
            }
            for audit in audits
        ],
    }


def measure_summary_runtime(
    rows: list[dict[str, object]],
    *,
    repeats: int = 3,
) -> dict[str, object]:
    """Measure deterministic summary cost using stdlib-only wall time and allocations."""

    from app.domain.recursive_summary import build_recursive_summary, render_recursive_summary

    sample_count = max(1, repeats)
    durations_ms: list[float] = []
    peak_bytes = 0
    source_count = len(rows)
    cited_count = 0
    for _ in range(sample_count):
        tracemalloc.start()
        started = time.perf_counter()
        summary = build_recursive_summary(rows)
        answer, cited_rows = render_recursive_summary(summary) if summary else ("", [])
        elapsed = (time.perf_counter() - started) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        durations_ms.append(round(elapsed, 3))
        peak_bytes = max(peak_bytes, peak)
        cited_count = len(cited_rows)

    return {
        "runs": sample_count,
        "source_rows": source_count,
        "cited_rows": cited_count,
        "first_ms": durations_ms[0],
        "median_ms": round(float(median(durations_ms)), 3),
        "max_ms": max(durations_ms),
        "peak_allocated_kib": round(peak_bytes / 1024, 1),
    }


def validate_cached_summary(
    answer: str,
    citations: list[dict[str, Any]],
    retrieval_meta: dict[str, object],
    active_rows: list[dict[str, object]] | None = None,
    document_id: str | None = None,
) -> dict[str, object]:
    """Validate cache metadata and citation wiring before exposing a cache hit."""

    from app.domain.recursive_summary import RECURSIVE_SUMMARY_VERSION

    hierarchy = retrieval_meta.get("summary_hierarchy")
    hierarchy_version = hierarchy.get("hierarchy_version") if isinstance(hierarchy, dict) else None
    audit = audit_citation_support(answer, _cache_citation_rows(citations, retrieval_meta, active_rows))
    issues: list[str] = []
    profile_version = str(retrieval_meta.get("summary_profile") or "")
    if (
        retrieval_meta.get("strategy") == "recursive_document_summary"
        and hierarchy_version is not None
        and hierarchy_version != RECURSIVE_SUMMARY_VERSION
    ):
        issues.append("summary_version_missing_or_stale")
    if f":{RECURSIVE_SUMMARY_VERSION}:" not in f":{profile_version}:":
        issues.append("summary_version_missing_or_stale")
    if active_rows is not None:
        active_ids = {str(row.get("id") or "") for row in active_rows}
        cited_ids = {str(item.get("chunk_id") or "") for item in citations}
        if not cited_ids <= active_ids:
            issues.append("citation_chunk_not_in_active_index")
        if document_id:
            if any(
                str(item.get("document_id") or "") not in {"", document_id}
                for item in citations
            ):
                issues.append("citation_document_scope_mismatch")
            if any(
                str(row.get("document_id") or "") not in {"", document_id}
                for row in active_rows
            ):
                issues.append("active_rows_scope_mismatch")
        if isinstance(hierarchy, dict):
            source_ids = {
                str(value)
                for value in hierarchy.get("source_chunk_ids", [])
                if value
            }
            if source_ids and not source_ids <= active_ids:
                issues.append("summary_source_not_in_active_index")
    if not audit["cache_safe"]:
        issues.append("citation_support_failed")
    return {
        "reliability_version": SUMMARY_RELIABILITY_VERSION,
        "cache_consistent": not issues,
        "issues": issues,
        "citation_support": audit,
    }


def _cache_citation_rows(
    citations: list[dict[str, Any]],
    retrieval_meta: dict[str, object],
    active_rows: list[dict[str, object]] | None,
) -> list[dict[str, Any]]:
    if active_rows is None:
        return citations
    active_by_id = {str(row.get("id") or ""): row for row in active_rows}
    anchor_map = retrieval_meta.get("citation_anchor_chunk_map")
    if isinstance(anchor_map, list):
        mapped: list[dict[str, Any]] = []
        for item in anchor_map:
            if not isinstance(item, dict):
                continue
            try:
                anchor = int(item.get("anchor"))
            except (TypeError, ValueError):
                continue
            row = active_by_id.get(str(item.get("chunk_id") or ""))
            if row is not None and anchor > 0:
                mapped.append({"anchor": anchor, "id": row.get("id"), "text": row.get("text")})
        if mapped:
            return mapped
    rows: list[dict[str, Any]] = []
    for anchor, citation in enumerate(citations, start=1):
        row = active_by_id.get(str(citation.get("chunk_id") or ""))
        if row is not None:
            rows.append({"anchor": anchor, "id": row.get("id"), "text": row.get("text")})
        else:
            rows.append({"anchor": anchor, **citation})
    return rows


def _claim_sentences(answer: str) -> list[str]:
    normalized_answer = re.sub(
        r"([.!?])[ \t]+((?:\[\d+\][ \t]*)+)",
        lambda match: f" {match.group(2).strip()}{match.group(1)} ",
        answer,
    )
    sentences: list[str] = []
    for line in normalized_answer.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence = sentence.strip(" -*")
            if len(re.sub(r"\[\d+\]", "", sentence).split()) >= 4:
                sentences.append(sentence)
    return sentences


def _support_score(sentence_terms: set[str], source_terms: set[str]) -> float:
    if not sentence_terms or not source_terms:
        return 0.0
    return len(sentence_terms & source_terms) / len(sentence_terms)


def _terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text.lower()):
        if token in _STOPWORDS:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        terms.add(token)
    return terms
