from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[5]
MODULE_PATH = WORKSPACE_ROOT / "scripts" / "validate_eval_gate.py"
spec = importlib.util.spec_from_file_location("validate_eval_gate", MODULE_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def test_generalization_gate_passes_when_dataset_and_metrics_meet_thresholds(tmp_path: Path) -> None:
    dataset = tmp_path / "gate.jsonl"
    rows = [
        {
            "id": "one",
            "source_file": "source-a.pdf",
            "category": "definition",
            "answerability": "answerable",
            "query": "Define the concept.",
            "expected_phrases": ["concept"],
        },
        {
            "id": "two",
            "source_file": "source-b.pdf",
            "category": "unanswerable",
            "answerability": "unanswerable",
            "query": "What unsupported fact is here?",
            "expected_phrases": [],
        },
    ]
    dataset.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    summary = validator.load_dataset_summary(dataset)
    manifest = {
        "version": "test",
        "mode": "bm25",
        "dataset_requirements": {
            "min_samples": 2,
            "min_source_files": 2,
            "min_unanswerable": 1,
            "required_categories": ["definition", "unanswerable"],
        },
        "thresholds": {
            "mrr": 0.7,
            "recall@8": 0.85,
            "answer_quality_metrics.pass_rate": 0.9,
            "answer_quality_metrics.faithfulness": 0.95,
        },
    }
    metrics = {
        "modes": ["bm25"],
        "results": {
            "bm25": {
                "mrr": 0.9,
                "recall@8": 1.0,
                "answer_quality_metrics": {
                    "pass_rate": 1.0,
                    "faithfulness": 0.99,
                },
            }
        },
    }

    result = validator.validate_gate(
        manifest=manifest,
        metrics=metrics,
        dataset_summary=summary,
    )

    assert result.passed is True
    assert not result.summary["failures"]


def test_generalization_gate_reports_missing_category_and_metric_failure(tmp_path: Path) -> None:
    dataset = tmp_path / "gate.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "one",
                "source_file": "source-a.pdf",
                "category": "definition",
                "answerability": "answerable",
                "query": "Define the concept.",
                "expected_phrases": ["concept"],
            }
        ),
        encoding="utf-8",
    )
    summary = validator.load_dataset_summary(dataset)
    manifest = {
        "version": "test",
        "mode": "bm25",
        "dataset_requirements": {
            "min_samples": 2,
            "min_source_files": 1,
            "min_unanswerable": 1,
            "required_categories": ["definition", "procedure"],
        },
        "thresholds": {
            "mrr": 0.7,
            "answer_quality_metrics.pass_rate": 0.9,
        },
    }
    metrics = {
        "modes": ["bm25"],
        "results": {
            "bm25": {
                "mrr": 0.5,
                "answer_quality_metrics": {
                    "pass_rate": 1.0,
                },
            }
        },
    }

    result = validator.validate_gate(
        manifest=manifest,
        metrics=metrics,
        dataset_summary=summary,
    )

    failed_names = {check["name"] for check in result.summary["failures"]}
    assert result.passed is False
    assert {"min_samples", "required_categories", "min_unanswerable", "mrr"} <= failed_names
