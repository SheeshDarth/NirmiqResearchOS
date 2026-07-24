from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GateResult:
    passed: bool
    checks: list[dict[str, object]]
    summary: dict[str, object]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate NIRMIQ eval metrics against a generalization gate manifest.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=WORKSPACE_ROOT / "data" / "processed" / "eval" / "generalization_gate.json",
        help="Gate manifest JSON path.",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=None,
        help="Metrics JSON path. Defaults to manifest.metrics_path.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Dataset JSONL path. Defaults to manifest.dataset_path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON report output path.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    return json.loads(resolved.read_text(encoding="utf-8"))


def resolve_path(path: Path | str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (WORKSPACE_ROOT / candidate).resolve()


def load_dataset_summary(path: Path) -> dict[str, object]:
    resolved = resolve_path(path)
    rows: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    answerability: dict[str, int] = {}
    source_files: set[str] = set()
    response_modes: dict[str, int] = {}

    for line_no, raw in enumerate(resolved.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw.strip():
            continue
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"Dataset line {line_no} must be a JSON object.")
        rows.append(payload)
        category = str(payload.get("category") or "uncategorized")
        categories[category] = categories.get(category, 0) + 1
        current_answerability = str(payload.get("answerability") or "answerable").lower()
        answerability[current_answerability] = answerability.get(current_answerability, 0) + 1
        source_file = str(payload.get("source_file") or "").strip()
        if source_file:
            source_files.add(source_file)
        response_mode = str(payload.get("response_mode") or "research")
        response_modes[response_mode] = response_modes.get(response_mode, 0) + 1

    return {
        "path": str(resolved.relative_to(WORKSPACE_ROOT) if resolved.is_relative_to(WORKSPACE_ROOT) else resolved),
        "samples": len(rows),
        "categories": dict(sorted(categories.items())),
        "category_count": len(categories),
        "answerability": dict(sorted(answerability.items())),
        "source_file_count": len(source_files),
        "source_files": sorted(source_files),
        "response_modes": dict(sorted(response_modes.items())),
    }


def validate_gate(
    *,
    manifest: dict[str, Any],
    metrics: dict[str, Any],
    dataset_summary: dict[str, object],
) -> GateResult:
    mode = str(manifest.get("mode") or first_mode(metrics))
    result = get_mode_result(metrics, mode)
    thresholds = manifest.get("thresholds") or {}
    dataset_requirements = manifest.get("dataset_requirements") or {}

    checks: list[dict[str, object]] = []
    add_dataset_checks(checks, dataset_summary, dataset_requirements)
    add_metric_checks(checks, result, thresholds)

    passed = all(bool(check["passed"]) for check in checks)
    summary = {
        "gate_version": manifest.get("version", "unknown"),
        "mode": mode,
        "passed": passed,
        "dataset": dataset_summary,
        "checked_metric_count": sum(1 for check in checks if check["kind"] == "metric"),
        "checked_dataset_count": sum(1 for check in checks if check["kind"] == "dataset"),
        "failures": [check for check in checks if not bool(check["passed"])],
    }
    return GateResult(passed=passed, checks=checks, summary=summary)


def add_dataset_checks(
    checks: list[dict[str, object]],
    dataset_summary: dict[str, object],
    requirements: dict[str, Any],
) -> None:
    samples = int(dataset_summary.get("samples") or 0)
    source_file_count = int(dataset_summary.get("source_file_count") or 0)
    categories = dataset_summary.get("categories") if isinstance(dataset_summary.get("categories"), dict) else {}
    answerability = dataset_summary.get("answerability") if isinstance(dataset_summary.get("answerability"), dict) else {}
    required_categories = [str(value) for value in requirements.get("required_categories", [])]
    missing_categories = [category for category in required_categories if category not in categories]

    add_check(
        checks,
        kind="dataset",
        name="min_samples",
        actual=samples,
        threshold=int(requirements.get("min_samples", 0)),
        passed=samples >= int(requirements.get("min_samples", 0)),
    )
    add_check(
        checks,
        kind="dataset",
        name="min_source_files",
        actual=source_file_count,
        threshold=int(requirements.get("min_source_files", 0)),
        passed=source_file_count >= int(requirements.get("min_source_files", 0)),
    )
    add_check(
        checks,
        kind="dataset",
        name="required_categories",
        actual=sorted(categories),
        threshold=required_categories,
        passed=not missing_categories,
        details={"missing_categories": missing_categories},
    )
    min_unanswerable = int(requirements.get("min_unanswerable", 0))
    unanswerable_count = int(answerability.get("unanswerable", 0))
    add_check(
        checks,
        kind="dataset",
        name="min_unanswerable",
        actual=unanswerable_count,
        threshold=min_unanswerable,
        passed=unanswerable_count >= min_unanswerable,
    )


def add_metric_checks(
    checks: list[dict[str, object]],
    result: dict[str, Any],
    thresholds: dict[str, Any],
) -> None:
    for name, minimum in sorted(thresholds.items()):
        actual = metric_value(result, name)
        if actual is None:
            add_check(
                checks,
                kind="metric",
                name=name,
                actual=None,
                threshold=minimum,
                passed=False,
                details={"reason": "metric_not_found"},
            )
            continue
        add_check(
            checks,
            kind="metric",
            name=name,
            actual=round(float(actual), 6),
            threshold=minimum,
            passed=float(actual) >= float(minimum),
        )


def metric_value(result: dict[str, Any], dotted_name: str) -> float | None:
    current: Any = result
    for part in dotted_name.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, (int, float)):
        return float(current)
    return None


def add_check(
    checks: list[dict[str, object]],
    *,
    kind: str,
    name: str,
    actual: object,
    threshold: object,
    passed: bool,
    details: dict[str, object] | None = None,
) -> None:
    checks.append(
        {
            "kind": kind,
            "name": name,
            "actual": actual,
            "threshold": threshold,
            "passed": passed,
            **({"details": details} if details else {}),
        }
    )


def first_mode(metrics: dict[str, Any]) -> str:
    modes = metrics.get("modes")
    if isinstance(modes, list) and modes:
        return str(modes[0])
    results = metrics.get("results")
    if isinstance(results, dict) and results:
        return str(next(iter(results)))
    raise ValueError("Metrics JSON does not contain any mode results.")


def get_mode_result(metrics: dict[str, Any], mode: str) -> dict[str, Any]:
    results = metrics.get("results")
    if not isinstance(results, dict) or mode not in results:
        raise ValueError(f"Metrics JSON does not contain result mode: {mode}")
    result = results[mode]
    if not isinstance(result, dict):
        raise ValueError(f"Metrics result for mode {mode} must be an object.")
    return result


def report_text(result: GateResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    lines = [f"NIRMIQ generalization gate: {status}"]
    for check in result.checks:
        marker = "OK" if check["passed"] else "FAIL"
        lines.append(
            f"- {marker} {check['kind']}:{check['name']} "
            f"actual={check['actual']} threshold={check['threshold']}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    manifest = load_json(args.manifest)
    metrics_path = args.metrics or Path(str(manifest.get("metrics_path") or ""))
    dataset_path = args.dataset or Path(str(manifest.get("dataset_path") or ""))
    if not str(metrics_path):
        raise ValueError("Metrics path must be provided by --metrics or manifest.metrics_path.")
    if not str(dataset_path):
        raise ValueError("Dataset path must be provided by --dataset or manifest.dataset_path.")

    metrics = load_json(metrics_path)
    dataset_summary = load_dataset_summary(dataset_path)
    result = validate_gate(manifest=manifest, metrics=metrics, dataset_summary=dataset_summary)
    payload = {
        **result.summary,
        "checks": result.checks,
    }
    print(report_text(result))
    if args.output:
        output_path = resolve_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
