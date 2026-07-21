from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[5] / "scripts" / "export_real_user_qa.py"
SPEC = importlib.util.spec_from_file_location("export_real_user_qa", SCRIPT_PATH)
assert SPEC and SPEC.loader
export_real_user_qa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export_real_user_qa)


def test_feedback_candidate_classifies_query_and_strips_source_path() -> None:
    candidate = export_real_user_qa.feedback_to_candidate(
        {
            "id": "abc1234567890",
            "rating": "needs_work",
            "query": "Compare CNNs and dense networks using diagrams.",
            "answer": "This answer mixed unrelated passages and did not cite the figure.",
            "document_id": "doc-1",
            "source_title": r"C:\Users\Siddharth\notes\ml textbook.pdf",
            "reason": "irrelevant evidence",
            "created_at": "2026-07-21T00:00:00+00:00",
        }
    )

    assert candidate["id"] == "feedback-abc123456789"
    assert candidate["category"] == "comparison"
    assert candidate["answerability"] == "unanswerable_or_weak_evidence"
    assert candidate["source_title"] == "ml textbook.pdf"
    assert candidate["review_status"] == "needs_human_labels"


def test_export_feedback_candidates_writes_local_report(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "nirmiq.db"
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute(
            """
            CREATE TABLE answer_feedback (
                id TEXT,
                session_id TEXT,
                rating TEXT,
                query TEXT,
                answer TEXT,
                document_id TEXT,
                source_title TEXT,
                reason TEXT,
                created_at TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO answer_feedback VALUES (
                'fb-1', 's-1', 'needs_work', 'Summarize chapter 3.',
                'Too broad and missing citations.', 'doc-1', 'chapter.pdf',
                'needs more evidence', '2026-07-21T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO answer_feedback VALUES (
                'fb-2', 's-1', 'good', 'Define retrieval.',
                'A useful answer.', 'doc-1', 'chapter.pdf',
                NULL, '2026-07-21T00:01:00+00:00'
            )
            """
        )

    output_path = tmp_path / "candidates.jsonl"
    report_path = tmp_path / "report.json"
    report = export_real_user_qa.export_feedback_candidates(
        sqlite_path=sqlite_path,
        output_path=output_path,
        report_path=report_path,
        include_good=False,
        limit=20,
    )

    assert report["candidate_count"] == 1
    assert report["category_counts"] == {"summary": 1}
    assert report["rating_counts"] == {"needs_work": 1}
    assert "feedback-fb-1" in output_path.read_text(encoding="utf-8")
    assert "local-only" in report_path.read_text(encoding="utf-8")
