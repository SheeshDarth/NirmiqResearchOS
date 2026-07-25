from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = WORKSPACE_ROOT / "data" / "processed" / "eval" / "generalization_gate.json"
DEFAULT_RAW_ROOT = WORKSPACE_ROOT / "data" / "raw"


@dataclass(frozen=True)
class EvalRow:
    sample_id: str
    query: str
    source_file: str
    category: str
    answerability: str
    expected_phrases: list[str]
    required_concepts: list[object]
    expected_answer: str
    response_mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit NIRMIQ eval dataset coverage and next expansion gaps.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Generalization gate manifest path.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Dataset JSONL path. Defaults to manifest.dataset_path.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="Local raw corpus root for unused-source inventory.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional JSON report output path.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Optional Markdown report output path.",
    )
    return parser.parse_args()


def resolve_path(path: Path | str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (WORKSPACE_ROOT / candidate).resolve()


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(resolve_path(path).read_text(encoding="utf-8"))


def load_rows(path: Path) -> list[EvalRow]:
    rows: list[EvalRow] = []
    for line_no, raw in enumerate(resolve_path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw.strip():
            continue
        payload = json.loads(raw)
        rows.append(
            EvalRow(
                sample_id=str(payload.get("id") or f"line-{line_no}").strip(),
                query=str(payload.get("query") or "").strip(),
                source_file=str(payload.get("source_file") or "").strip(),
                category=str(payload.get("category") or "uncategorized").strip(),
                answerability=str(payload.get("answerability") or "answerable").strip().lower(),
                expected_phrases=[
                    str(value).strip()
                    for value in payload.get("expected_phrases", [])
                    if str(value).strip()
                ],
                required_concepts=list(payload.get("required_concepts") or []),
                expected_answer=str(payload.get("expected_answer") or "").strip(),
                response_mode=str(payload.get("response_mode") or "research").strip() or "research",
            )
        )
    return rows


def audit_dataset(
    *,
    rows: list[EvalRow],
    manifest: dict[str, Any],
    raw_root: Path,
) -> dict[str, Any]:
    dataset_requirements = manifest.get("dataset_requirements") or {}
    expansion_requirements = manifest.get("expansion_requirements") or {}
    categories = Counter(row.category for row in rows)
    answerability = Counter(row.answerability for row in rows)
    response_modes = Counter(row.response_mode for row in rows)
    source_files = sorted({row.source_file for row in rows if row.source_file})
    source_extension_counts = Counter(source_extension(path) for path in source_files)
    source_family_counts = Counter(source_family(path) for path in source_files)

    query_duplicates = duplicate_values(row.query.lower() for row in rows if row.query)
    answerable_rows = [row for row in rows if row.answerability != "unanswerable"]
    label_quality = {
        "answerable_rows": len(answerable_rows),
        "missing_expected_answer": [
            row.sample_id for row in answerable_rows if not row.expected_answer
        ],
        "missing_required_concepts": [
            row.sample_id for row in answerable_rows if not row.required_concepts
        ],
        "missing_expected_phrases": [
            row.sample_id for row in answerable_rows if not row.expected_phrases
        ],
        "duplicate_queries": query_duplicates,
    }

    existing_sources = []
    missing_sources = []
    for source in source_files:
        resolved = resolve_path(source)
        if resolved.exists():
            existing_sources.append(source)
        else:
            missing_sources.append(source)

    raw_sources = raw_source_inventory(resolve_path(raw_root))
    used_source_keys = {
        key
        for source in source_files
        for key in comparable_source_keys(source)
    }
    unused_sources = [
        source
        for source in raw_sources
        if normalize_source_key(str(source["path"])) not in used_source_keys
    ]

    min_per_category = int(expansion_requirements.get("min_per_category_next", 3))
    target_samples_next = int(
        expansion_requirements.get(
            "target_samples_next",
            dataset_requirements.get("target_samples_next", dataset_requirements.get("min_samples", 0)),
        )
    )
    target_source_files_next = int(
        expansion_requirements.get(
            "target_source_files_next",
            dataset_requirements.get("target_source_files_next", dataset_requirements.get("min_source_files", 0)),
        )
    )
    target_unanswerable_next = int(expansion_requirements.get("target_unanswerable_next", 10))
    target_categories_next = [
        str(value)
        for value in expansion_requirements.get("target_categories_next", [])
    ]
    missing_target_categories = [
        category for category in target_categories_next if category not in categories
    ]
    underrepresented_categories = {
        category: count
        for category, count in sorted(categories.items())
        if count < min_per_category
    }

    source_type_targets = expansion_requirements.get("target_source_families_next", [])
    missing_source_families = [
        str(source_family_name)
        for source_family_name in source_type_targets
        if str(source_family_name) not in source_family_counts
    ]

    return {
        "version": "eval-dataset-audit-v1",
        "dataset": {
            "samples": len(rows),
            "categories": dict(sorted(categories.items())),
            "category_count": len(categories),
            "answerability": dict(sorted(answerability.items())),
            "response_modes": dict(sorted(response_modes.items())),
            "source_file_count": len(source_files),
            "source_files": source_files,
            "source_extension_counts": dict(sorted(source_extension_counts.items())),
            "source_family_counts": dict(sorted(source_family_counts.items())),
            "existing_source_count": len(existing_sources),
            "missing_source_files": missing_sources,
        },
        "label_quality": label_quality,
        "raw_corpus": {
            "root": relative_or_absolute(resolve_path(raw_root)),
            "source_count": len(raw_sources),
            "unused_source_count": len(unused_sources),
            "unused_sources": unused_sources,
        },
        "expansion_gap": {
            "target_samples_next": target_samples_next,
            "samples_to_target": max(0, target_samples_next - len(rows)),
            "target_source_files_next": target_source_files_next,
            "source_files_to_target": max(0, target_source_files_next - len(source_files)),
            "target_unanswerable_next": target_unanswerable_next,
            "unanswerable_to_target": max(0, target_unanswerable_next - answerability.get("unanswerable", 0)),
            "min_per_category_next": min_per_category,
            "underrepresented_categories": underrepresented_categories,
            "missing_target_categories": missing_target_categories,
            "missing_source_families": missing_source_families,
        },
        "next_labeling_priorities": next_labeling_priorities(
            categories=categories,
            missing_target_categories=missing_target_categories,
            underrepresented_categories=underrepresented_categories,
            unused_sources=unused_sources,
        ),
    }


def duplicate_values(values: object) -> list[dict[str, object]]:
    counts = Counter(values)
    return [
        {"value": value, "count": count}
        for value, count in sorted(counts.items())
        if count > 1
    ]


def source_extension(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return suffix or "unknown"


def source_family(path: str) -> str:
    normalized = normalize_source_key(path)
    if "/golden_demo/" in normalized:
        return "golden_demo"
    if "/demo_pdfs/" in normalized:
        return "demo_pdf"
    if normalized.startswith("temp/hard-document-fixtures/"):
        return "hard_fixture"
    if "hands-on-machine-learning" in normalized:
        return "textbook"
    if "attention_is_all_you_need" in normalized:
        return "research_paper"
    if "mod-5-gen-ai" in normalized:
        return "module_notes"
    if "prompt-engineering" in normalized:
        return "prompt_engineering"
    if "website-building-guide" in normalized:
        return "technical_guide"
    return "other"


def raw_source_inventory(raw_root: Path) -> list[dict[str, object]]:
    if not raw_root.exists():
        return []
    records: list[dict[str, object]] = []
    seen_content_keys: dict[tuple[int, str], list[str]] = defaultdict(list)
    for path in sorted(raw_root.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = relative_or_absolute(path)
        content_key = (path.stat().st_size, path.suffix.lower())
        seen_content_keys[content_key].append(rel)
        records.append(
            {
                "path": rel,
                "extension": source_extension(rel),
                "family": source_family(rel),
                "size_bytes": path.stat().st_size,
            }
        )

    duplicate_groups = {
        path: len(paths)
        for paths in seen_content_keys.values()
        if len(paths) > 1
        for path in paths
    }
    for record in records:
        duplicate_count = duplicate_groups.get(str(record["path"]), 1)
        if duplicate_count > 1:
            record["same_size_extension_group_size"] = duplicate_count
    return records


def next_labeling_priorities(
    *,
    categories: Counter[str],
    missing_target_categories: list[str],
    underrepresented_categories: dict[str, int],
    unused_sources: list[dict[str, object]],
) -> list[str]:
    priorities: list[str] = []
    if missing_target_categories:
        priorities.append(
            "Add reviewed labels for missing target categories: "
            + ", ".join(missing_target_categories)
            + "."
        )
    if underrepresented_categories:
        ranked = ", ".join(
            f"{category}({count})" for category, count in sorted(underrepresented_categories.items())
        )
        priorities.append(f"Raise thin categories to at least three labels each: {ranked}.")
    unused_by_family = Counter(str(source["family"]) for source in unused_sources)
    candidate_families = [
        family for family, count in unused_by_family.most_common() if family not in {"other"}
    ]
    if candidate_families:
        priorities.append(
            "Review unused local source families for fresh labels: "
            + ", ".join(candidate_families[:5])
            + "."
        )
    if categories.get("unanswerable", 0) < 10:
        priorities.append("Add more unanswerable and partial-answer prompts to test abstention.")
    priorities.append("Keep at least one blind holdout split that is not tuned after failures are seen.")
    return priorities


def normalize_source_key(path: str) -> str:
    return path.replace("\\", "/").lower().lstrip("./")


def comparable_source_keys(path: str) -> set[str]:
    """Return stable keys for comparing absolute and repo-relative source paths."""
    keys = {normalize_source_key(path)}
    try:
        keys.add(normalize_source_key(relative_or_absolute(resolve_path(path))))
    except OSError:
        keys.add(normalize_source_key(str(resolve_path(path))))
    return {key for key in keys if key}


def relative_or_absolute(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(WORKSPACE_ROOT)).replace("/", "\\")
    except ValueError:
        return str(resolved)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    output_path = resolve_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    output_path = resolve_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(payload), encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    dataset = payload["dataset"]
    gap = payload["expansion_gap"]
    label_quality = payload["label_quality"]
    raw_corpus = payload["raw_corpus"]
    lines = [
        "# NIRMIQ Eval Dataset Audit",
        "",
        "Generated by `scripts/audit_eval_dataset.py`.",
        "",
        "## Current Coverage",
        "",
        f"- Samples: `{dataset['samples']}`",
        f"- Source files used: `{dataset['source_file_count']}`",
        f"- Categories: `{dataset['category_count']}`",
        f"- Existing source files: `{dataset['existing_source_count']}`",
        f"- Missing source files: `{len(dataset['missing_source_files'])}`",
        "",
        "### Categories",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in dataset["categories"].items():
        lines.append(f"| {category} | {count} |")

    lines.extend(
        [
            "",
            "### Answerability",
            "",
            "| Answerability | Count |",
            "| --- | ---: |",
        ]
    )
    for answerability, count in dataset["answerability"].items():
        lines.append(f"| {answerability} | {count} |")

    lines.extend(
        [
            "",
            "## Expansion Gap",
            "",
            f"- Samples to next target: `{gap['samples_to_target']}` of `{gap['target_samples_next']}`",
            f"- Source files to next target: `{gap['source_files_to_target']}` of `{gap['target_source_files_next']}`",
            f"- Unanswerable prompts to target: `{gap['unanswerable_to_target']}` of `{gap['target_unanswerable_next']}`",
            f"- Missing target categories: `{', '.join(gap['missing_target_categories']) or 'none'}`",
            f"- Missing source families: `{', '.join(gap['missing_source_families']) or 'none'}`",
            "",
            "### Underrepresented Categories",
            "",
            "| Category | Current Count |",
            "| --- | ---: |",
        ]
    )
    underrepresented = gap["underrepresented_categories"]
    if underrepresented:
        for category, count in underrepresented.items():
            lines.append(f"| {category} | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Label Quality Warnings",
            "",
            f"- Duplicate queries: `{len(label_quality['duplicate_queries'])}`",
            f"- Answerable rows missing expected answer: `{len(label_quality['missing_expected_answer'])}`",
            f"- Answerable rows missing required concepts: `{len(label_quality['missing_required_concepts'])}`",
            f"- Answerable rows missing expected phrases: `{len(label_quality['missing_expected_phrases'])}`",
            "",
            "## Raw Corpus",
            "",
            f"- Raw corpus root: `{raw_corpus['root']}`",
            f"- Raw sources found: `{raw_corpus['source_count']}`",
            f"- Raw sources unused by current gate: `{raw_corpus['unused_source_count']}`",
            "",
            "## Next Labeling Priorities",
            "",
        ]
    )
    for priority in payload["next_labeling_priorities"]:
        lines.append(f"- {priority}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    dataset_path = args.dataset or Path(str(manifest.get("dataset_path") or ""))
    if not str(dataset_path):
        raise ValueError("Dataset path must be provided by --dataset or manifest.dataset_path.")
    report = audit_dataset(
        rows=load_rows(dataset_path),
        manifest=manifest,
        raw_root=args.raw_root,
    )
    print(render_markdown(report))
    if args.json_output:
        write_json(args.json_output, report)
    if args.markdown_output:
        write_markdown(args.markdown_output, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
