from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SQLITE_PATH = Path("data/sqlite/nirmiq.db")
DEFAULT_OUTPUT = Path("temp/real_user_qa/local_feedback_eval_candidates.jsonl")
DEFAULT_REPORT = Path("temp/real_user_qa/local_feedback_report.json")


def classify_query(query: str) -> str:
    normalized = _normalize(query)
    if _contains_any(normalized, ("summarize", "summary", "main idea", "overview")):
        return "summary"
    if _contains_any(normalized, ("compare", "difference", "versus", " vs ", "distinguish")):
        return "comparison"
    if _contains_any(normalized, ("steps", "procedure", "workflow", "how to", "process")):
        return "procedure"
    if _contains_any(normalized, ("limitation", "drawback", "disadvantage", "caveat")):
        return "limitations"
    if _contains_any(normalized, ("diagram", "image", "figure", "table", "equation", "formula")):
        return "visual_or_structural"
    if _contains_any(normalized, ("exam", "marks", "question bank", "study guide")):
        return "exam"
    if _contains_any(normalized, ("paper", "citation", "related work", "literature")):
        return "paper"
    if _contains_any(normalized, ("what is", "define", "meaning", "explain")):
        return "explanation"
    return "factual_lookup"


def infer_answerability(query: str, reason: str | None) -> str:
    combined = _normalize(f"{query} {reason or ''}")
    unsupported_markers = (
        "not in source",
        "not found",
        "unsupported",
        "outside",
        "no evidence",
        "needs more evidence",
        "hallucinat",
        "irrelevant",
    )
    if _contains_any(combined, unsupported_markers):
        return "unanswerable_or_weak_evidence"
    return "answerable_candidate"


def feedback_to_candidate(row: dict[str, Any]) -> dict[str, Any]:
    feedback_id = str(row.get("id") or "unknown")
    query = str(row.get("query") or "").strip()
    reason = _clean_optional(row.get("reason"))
    return {
        "id": f"feedback-{feedback_id[:12]}",
        "review_status": "needs_human_labels",
        "rating": str(row.get("rating") or "").strip() or "unknown",
        "category": classify_query(query),
        "answerability": infer_answerability(query, reason),
        "query": query,
        "source_title": safe_source_label(row.get("source_title")),
        "document_id": _clean_optional(row.get("document_id")),
        "reason": reason,
        "answer_excerpt": compact_text(str(row.get("answer") or ""), limit=700),
        "created_at": _clean_optional(row.get("created_at")),
        "labeling_next_step": (
            "Open the source locally, add expected_phrases/required_concepts/page hints, "
            "then promote this record into a tracked eval dataset."
        ),
    }


def export_feedback_candidates(
    sqlite_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    include_good: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    rows = read_feedback(sqlite_path, include_good=include_good, limit=limit)
    candidates = [feedback_to_candidate(row) for row in rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")

    category_counts = Counter(candidate["category"] for candidate in candidates)
    rating_counts = Counter(candidate["rating"] for candidate in candidates)
    answerability_counts = Counter(candidate["answerability"] for candidate in candidates)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sqlite_path": str(sqlite_path),
        "output_path": str(output_path),
        "candidate_count": len(candidates),
        "include_good": include_good,
        "limit": limit,
        "category_counts": dict(sorted(category_counts.items())),
        "rating_counts": dict(sorted(rating_counts.items())),
        "answerability_counts": dict(sorted(answerability_counts.items())),
        "privacy_note": (
            "This report is local-only by default. Do not commit generated candidates "
            "unless they have been manually reviewed and scrubbed."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def read_feedback(sqlite_path: Path, *, include_good: bool, limit: int) -> list[dict[str, Any]]:
    if not sqlite_path.exists():
        return []
    where_clause = "" if include_good else "WHERE rating = 'needs_work'"
    safe_limit = max(1, min(limit, 1000))
    query = f"""
        SELECT id, session_id, rating, query, answer, document_id, source_title, reason, created_at
        FROM answer_feedback
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ?
    """
    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(query, (safe_limit,)).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower():
                return []
            raise
    return [dict(row) for row in rows]


def safe_source_label(value: object) -> str | None:
    label = _clean_optional(value)
    if label is None:
        return None
    label = label.replace("\\", "/")
    return label.rsplit("/", 1)[-1]


def compact_text(text: str, *, limit: int) -> str:
    compacted = re.sub(r"\s+", " ", text).strip()
    if len(compacted) <= limit:
        return compacted
    return compacted[: max(0, limit - 1)].rstrip() + "…"


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize(text: str) -> str:
    return f" {re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()} "


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export local NIRMIQ answer feedback into reviewable real-user QA candidates."
    )
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_PATH", str(DEFAULT_SQLITE_PATH)),
        help="Path to the local NIRMIQ SQLite database.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSONL candidate output path.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="JSON summary report output path.")
    parser.add_argument("--include-good", action="store_true", help="Include good feedback, not only needs_work.")
    parser.add_argument("--limit", type=int, default=200, help="Maximum feedback records to export.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = export_feedback_candidates(
        sqlite_path=Path(args.sqlite_path),
        output_path=Path(args.output),
        report_path=Path(args.report),
        include_good=bool(args.include_good),
        limit=int(args.limit),
    )
    print(
        "REAL_USER_QA_EXPORT "
        f"candidates={report['candidate_count']} "
        f"output={report['output_path']} "
        f"report={args.report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
