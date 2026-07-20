from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.domain.recursive_summary import build_recursive_summary, render_recursive_summary  # noqa: E402
from app.domain.summary_reliability import (  # noqa: E402
    audit_citation_support,
    measure_summary_runtime,
)


def _row(index: int, heading: str, text: str, *, section_id: str | None = None) -> dict[str, object]:
    return {
        "id": f"adversarial-{index}",
        "document_id": "adversarial-doc",
        "chunk_index": index,
        "page_start": index + 1,
        "page_end": index + 1,
        "text": text,
        "quality_score": 1.0,
        "section_id": section_id or f"section-{index}",
        "heading": heading,
        "section_path": heading,
        "chunk_type": "body",
    }


def build_cases() -> dict[str, list[dict[str, object]]]:
    return {
        "hostile_front_back_matter": [
            _row(0, "Contents", "Chapter 1 Foundations 1, Chapter 2 Validation 4, Appendix A Equations 8"),
            _row(1, "Chapter 1 Foundations", "Chapter 1 Foundations define the signal problem and the evidence needed to measure it."),
            _row(2, "1.1 Measurement", "Adaptive sampling observes signal variation before changing the measurement interval."),
            _row(3, "Chapter 2 Validation", "Chapter 2 Validation compares measured behavior with a known target and reports error."),
            _row(4, "Appendix A. Equations", "The stability margin is calculated as M = (target - measured) / max(abs(target), epsilon)."),
            _row(5, "Index", "adaptive sampling, 2, 3, 4, actuator, 8, calibration, 9, comparator, 10, controller, 11, drift, 12, error, 14"),
            _row(6, "Index", "feedback, 15, measurement, 16, margin, 17, signal, 18, stability, 19, target, 20, validation, 21"),
            _row(7, "Index", "actuator, adaptive, calibration, comparator, controller, drift, error, feedback, measurement, margin, signal, stability, target"),
            _row(8, "Index", "bibliography references appendix chapter contents copyright all rights reserved"),
        ],
        "duplicate_ocr_and_structure": [
            _row(0, "Chapter 1. Training", "Chapter 1. Training LetÃ¢Â€Â™s compare the modelÃ¢Â€Â™s output with the target."),
            _row(1, "Chapter 1. Training", "Training updates parameters after comparing a prediction with a measured target."),
            _row(2, "Chapter 3. Validation", "Chapter 3. Validation Validation checks generalization on observations not used for fitting."),
            _row(3, "Chapter 3. Validation", "The validation result is useful only when the held-out observations are representative."),
            _row(4, "False chapter reference", "The exercise refers to Chapter 9 but this paragraph describes an ordinary procedure."),
            _row(5, "Diagram", "Figure 1 shows the sensor, comparator, controller, and actuator feedback chain."),
        ],
        "mixed_equation_table_diagram": [
            _row(0, "Chapter 1. Control", "The stability margin is calculated as M = (target - measured) / max(abs(target), epsilon)."),
            _row(1, "Chapter 1. Control", "Low drift | below 0.5 percent per hour | monitor normally."),
            _row(2, "Chapter 1. Control", "High drift | above 2.0 percent per hour | recalibrate immediately."),
            _row(3, "Chapter 1. Control", "Figure 2 shows the feedback loop from sensor to comparator to controller."),
            _row(4, "Chapter 2. Limits", "Although the method reduces redundant measurements, a threshold that is too high can miss short events."),
        ],
    }


def evaluate(output: Path | None = None) -> int:
    results: dict[str, object] = {
        "version": "recursive-summary-reliability-v1",
        "strategy": "adversarial_structure_and_citation_support",
        "cases": {},
        "failures": [],
    }
    failures: list[str] = []
    for name, rows in build_cases().items():
        summary = build_recursive_summary(rows)
        if summary is None:
            failures.append(f"{name}: summary was empty")
            continue
        answer, cited_rows = render_recursive_summary(summary)
        audit = audit_citation_support(answer, cited_rows)
        repeat_answer, repeat_rows = render_recursive_summary(build_recursive_summary(rows))  # type: ignore[arg-type]
        runtime = measure_summary_runtime(rows)
        case_result = {
            "source_rows": len(rows),
            "cited_rows": len(cited_rows),
            "section_count": summary.section_count,
            "chapter_count": summary.chapter_count,
            "filtered_non_content_count": summary.filtered_non_content_count,
            "citation_audit": audit,
            "runtime": runtime,
            "deterministic": answer == repeat_answer and [row["id"] for row in cited_rows] == [row["id"] for row in repeat_rows],
        }
        results["cases"][name] = case_result  # type: ignore[index]
        if not case_result["deterministic"]:
            failures.append(f"{name}: output was not deterministic")
        if audit["invalid_anchor_count"] or not audit["cache_safe"]:
            failures.append(f"{name}: citation support audit failed")
        if audit["sentence_count"] != audit["cited_sentence_count"]:
            failures.append(f"{name}: uncited claim line detected")
        if runtime["max_ms"] > 250:
            failures.append(f"{name}: synthetic summary exceeded 250 ms")
        if runtime["peak_allocated_kib"] > 512:
            failures.append(f"{name}: synthetic allocation exceeded 512 KiB")
        expected_fragments = {
            "hostile_front_back_matter": ["Adaptive sampling", "stability margin"],
            "duplicate_ocr_and_structure": ["Let's compare", "feedback chain"],
            "mixed_equation_table_diagram": ["M =", "Figure 2", "miss short events"],
        }[name]
        missing_fragments = [fragment for fragment in expected_fragments if fragment not in answer]
        if missing_fragments:
            failures.append(f"{name}: expected source fact missing: {missing_fragments}")
        if name == "hostile_front_back_matter" and "adaptive sampling, 2, 3, 4" in answer:
            failures.append(f"{name}: index noise leaked into summary")

    results["case_count"] = len(results["cases"])  # type: ignore[arg-type]
    results["passed"] = not failures
    results["failures"] = failures
    encoded = json.dumps(results, indent=2, ensure_ascii=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline recursive-summary reliability gate.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    return evaluate(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
