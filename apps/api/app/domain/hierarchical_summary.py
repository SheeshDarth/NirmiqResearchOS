from dataclasses import dataclass
import math
import re


HIERARCHICAL_SUMMARY_VERSION = "hierarchical-extractive-v1"


@dataclass(frozen=True)
class SummarySeed:
    row: dict[str, object]
    coverage_key: str
    label: str


def select_hierarchical_summary_seeds(
    rows: list[dict[str, object]],
    *,
    max_seeds: int = 8,
) -> tuple[list[SummarySeed], dict[str, object]]:
    """Select original chunks across a document's hierarchy or page span."""

    if not rows or max_seeds <= 0:
        return [], {
            "hierarchy_version": HIERARCHICAL_SUMMARY_VERSION,
            "coverage_groups": 0,
            "selected_groups": [],
            "source_chunk_ids": [],
        }

    ordered = sorted(
        (row for row in rows if _is_readable(row)),
        key=lambda row: (
            int(row.get("page_start") or 1_000_000),
            str(row.get("id") or ""),
        ),
    )
    if not ordered:
        return [], {
            "hierarchy_version": HIERARCHICAL_SUMMARY_VERSION,
            "coverage_groups": 0,
            "selected_groups": [],
            "source_chunk_ids": [],
        }

    groups = _group_rows(ordered=ordered, max_seeds=max_seeds)
    representatives = [
        SummarySeed(
            row=max(group_rows, key=_seed_score),
            coverage_key=group_key,
            label=_group_label(group_key=group_key, rows=group_rows),
        )
        for group_key, group_rows in groups
    ]
    selected = _evenly_spaced(representatives, limit=max_seeds)
    return selected, {
        "hierarchy_version": HIERARCHICAL_SUMMARY_VERSION,
        "coverage_groups": len(groups),
        "selected_groups": [seed.coverage_key for seed in selected],
        "selected_labels": [seed.label for seed in selected],
        "source_chunk_ids": [str(seed.row.get("id") or "") for seed in selected],
        "provenance": "original_document_chunks",
    }


def _group_rows(
    *,
    ordered: list[dict[str, object]],
    max_seeds: int,
) -> list[tuple[str, list[dict[str, object]]]]:
    section_groups: dict[str, list[dict[str, object]]] = {}
    section_order: list[str] = []
    for row in ordered:
        key = _section_key(row)
        if not key:
            continue
        if key not in section_groups:
            section_groups[key] = []
            section_order.append(key)
        section_groups[key].append(row)

    # Use real section boundaries when they cover enough of the document.
    covered = sum(len(section_groups[key]) for key in section_order)
    if len(section_order) >= min(3, max_seeds) and covered >= math.ceil(len(ordered) * 0.6):
        return [(key, section_groups[key]) for key in section_order]

    bucket_count = min(max_seeds, len(ordered))
    bucket_size = max(1, math.ceil(len(ordered) / bucket_count))
    return [
        (f"document-region-{index + 1}", ordered[start : start + bucket_size])
        for index, start in enumerate(range(0, len(ordered), bucket_size))
    ]


def _section_key(row: dict[str, object]) -> str:
    path = re.sub(r"\s+", " ", str(row.get("section_path") or "")).strip(" /.-")
    heading = re.sub(r"\s+", " ", str(row.get("heading") or "")).strip(" /.-")
    raw = path or heading
    if not raw:
        return ""
    parts = [part.strip() for part in re.split(r"\s*(?:>|/|::)\s*", raw) if part.strip()]
    return " > ".join(parts[:2])[:160]


def _group_label(*, group_key: str, rows: list[dict[str, object]]) -> str:
    if not group_key.startswith("document-region-"):
        return group_key
    pages = [int(row["page_start"]) for row in rows if row.get("page_start") is not None]
    if not pages:
        return group_key.replace("-", " ").title()
    return f"Pages {min(pages)}-{max(pages)}"


def _is_readable(row: dict[str, object]) -> bool:
    text = re.sub(r"\s+", " ", str(row.get("text") or "")).strip()
    if len(text.split()) < 20:
        return False
    lowered = text.lower()
    return not any(
        marker in lowered
        for marker in (
            "all rights reserved",
            "permission to reproduce",
            "isbn ",
            "bibliography",
        )
    )


def _seed_score(row: dict[str, object]) -> tuple[float, int, str]:
    text = re.sub(r"\s+", " ", str(row.get("text") or "")).strip()
    lowered = text.lower()
    quality = float(row.get("quality_score") or 1.0)
    word_count = len(text.split())
    structure_bonus = sum(
        0.45
        for cue in (
            "overview",
            "introduction",
            "this chapter",
            "this section",
            "main ",
            "method",
            "result",
            "conclusion",
            "limitation",
        )
        if cue in lowered
    )
    length_bonus = 0.6 if 60 <= word_count <= 240 else 0.2 if word_count <= 320 else 0.0
    page = int(row.get("page_start") or 1_000_000)
    return quality + structure_bonus + length_bonus, -page, str(row.get("id") or "")


def _evenly_spaced(items: list[SummarySeed], *, limit: int) -> list[SummarySeed]:
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    indices = {
        round(index * (len(items) - 1) / (limit - 1))
        for index in range(limit)
    }
    return [items[index] for index in sorted(indices)]
