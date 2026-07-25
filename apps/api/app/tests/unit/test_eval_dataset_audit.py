from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[5]
MODULE_PATH = WORKSPACE_ROOT / "scripts" / "audit_eval_dataset.py"
spec = importlib.util.spec_from_file_location("audit_eval_dataset", MODULE_PATH)
assert spec and spec.loader
audit_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit_module
spec.loader.exec_module(audit_module)


def test_eval_dataset_audit_reports_expansion_gaps(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    (raw_root / "paper.pdf").write_text("paper", encoding="utf-8")
    (raw_root / "notes.md").write_text("notes", encoding="utf-8")
    dataset = tmp_path / "labels.jsonl"
    rows = [
        {
            "id": "one",
            "source_file": str(raw_root / "paper.pdf"),
            "category": "definition",
            "answerability": "answerable",
            "query": "Define attention.",
            "expected_answer": "Attention weights values.",
            "expected_phrases": ["attention weights values"],
            "required_concepts": [["attention"], ["values"]],
        },
        {
            "id": "two",
            "source_file": str(raw_root / "paper.pdf"),
            "category": "unanswerable",
            "answerability": "unanswerable",
            "query": "What launch date is mentioned?",
            "expected_phrases": [],
            "required_concepts": [],
        },
    ]
    dataset.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    manifest = {
        "dataset_requirements": {"min_samples": 2, "min_source_files": 1},
        "expansion_requirements": {
            "target_samples_next": 5,
            "target_source_files_next": 2,
            "target_unanswerable_next": 2,
            "min_per_category_next": 3,
            "target_categories_next": ["definition", "procedure", "unanswerable"],
            "target_source_families_next": ["other"],
        },
    }

    report = audit_module.audit_dataset(
        rows=audit_module.load_rows(dataset),
        manifest=manifest,
        raw_root=raw_root,
    )

    assert report["dataset"]["samples"] == 2
    assert report["expansion_gap"]["samples_to_target"] == 3
    assert report["expansion_gap"]["source_files_to_target"] == 1
    assert report["expansion_gap"]["unanswerable_to_target"] == 1
    assert "procedure" in report["expansion_gap"]["missing_target_categories"]
    assert report["raw_corpus"]["unused_source_count"] == 1


def test_eval_dataset_audit_flags_missing_label_quality_fields(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    source = raw_root / "source.pdf"
    source.write_text("source", encoding="utf-8")
    dataset = tmp_path / "labels.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "one",
                "source_file": str(source),
                "category": "definition",
                "answerability": "answerable",
                "query": "Define the idea.",
                "expected_phrases": [],
                "required_concepts": [],
            }
        ),
        encoding="utf-8",
    )

    report = audit_module.audit_dataset(
        rows=audit_module.load_rows(dataset),
        manifest={"expansion_requirements": {}},
        raw_root=raw_root,
    )

    quality = report["label_quality"]
    assert quality["missing_expected_answer"] == ["one"]
    assert quality["missing_expected_phrases"] == ["one"]
    assert quality["missing_required_concepts"] == ["one"]
