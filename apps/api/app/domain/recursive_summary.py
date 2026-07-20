from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import math
import re


RECURSIVE_SUMMARY_VERSION = "recursive-extractive-v6"

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
    "the",
    "their",
    "these",
    "this",
    "through",
    "using",
    "which",
    "will",
    "with",
}

_LOW_VALUE_MARKERS = (
    "all rights reserved",
    "copyright",
    "isbn ",
    "permission to reproduce",
    "trademark",
)


@dataclass(frozen=True)
class SummaryFact:
    text: str
    source_row: dict[str, object]
    score: float
    category: str

    @property
    def chunk_id(self) -> str:
        return str(self.source_row.get("id") or "")


@dataclass(frozen=True)
class SummaryNode:
    node_id: str
    label: str
    kind: str
    page_start: int | None
    page_end: int | None
    facts: tuple[SummaryFact, ...]
    source_chunk_ids: tuple[str, ...]
    children: tuple[SummaryNode, ...] = ()


@dataclass(frozen=True)
class RecursiveSummary:
    root: SummaryNode
    display_nodes: tuple[SummaryNode, ...]
    ordered_rows: tuple[dict[str, object], ...]
    section_count: int
    chapter_count: int
    reduction_depth: int
    filtered_non_content_count: int = 0

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "hierarchy_version": RECURSIVE_SUMMARY_VERSION,
            "strategy": "all_chunk_section_map_recursive_reduce",
            "source_chunks_considered": len(self.ordered_rows),
            "sections_considered": self.section_count,
            "chapter_groups": self.chapter_count,
            "display_groups": len(self.display_nodes),
            "reduction_depth": self.reduction_depth,
            "non_content_chunks_filtered": self.filtered_non_content_count,
            "source_chunk_ids": [str(row.get("id") or "") for row in self.ordered_rows],
            "provenance": "original_document_chunks",
        }


def build_recursive_summary(
    rows: list[dict[str, object]],
    *,
    max_display_groups: int = 24,
    reduction_fanout: int = 6,
) -> RecursiveSummary | None:
    """Map every readable chunk into sections, then reduce sections recursively."""

    ordered = tuple(sorted((row for row in rows if _is_readable(row)), key=_row_order))
    if not ordered:
        return None

    eligible_rows, filtered_non_content_count = _exclude_late_index_region(list(ordered))
    section_nodes = tuple(_build_section_nodes(eligible_rows))
    if not section_nodes:
        return None
    chapter_nodes = tuple(_build_chapter_nodes(list(section_nodes)))
    display_source = [node for node in chapter_nodes if node.label != "Front matter"]
    if not display_source:
        display_source = list(chapter_nodes)
    display_nodes = tuple(
        _coalesce_for_display(display_source, limit=max(1, max_display_groups))
    )
    root, reduction_depth = _reduce_to_root(
        display_source,
        fanout=max(2, reduction_fanout),
    )
    return RecursiveSummary(
        root=root,
        display_nodes=display_nodes,
        ordered_rows=ordered,
        section_count=len(section_nodes),
        chapter_count=len(display_source),
        reduction_depth=reduction_depth,
        filtered_non_content_count=filtered_non_content_count,
    )


def render_recursive_summary(
    summary: RecursiveSummary,
) -> tuple[str, list[dict[str, object]]]:
    """Render readable Markdown and return cited original rows in anchor order."""

    cited_rows: list[dict[str, object]] = []
    anchors: dict[str, int] = {}

    def anchor(fact: SummaryFact) -> int:
        chunk_id = fact.chunk_id
        if chunk_id not in anchors:
            anchors[chunk_id] = len(cited_rows) + 1
            cited_rows.append(fact.source_row)
        return anchors[chunk_id]

    overview_facts = _progressive_overview_facts(summary)
    lines = ["## Document summary", "", "### Overview"]
    for fact in overview_facts:
        lines.append(f"- {fact.text} [{anchor(fact)}]")

    guide_label = "Chapter-by-chapter" if any(
        node.kind == "chapter" for node in summary.display_nodes
    ) else "Section guide"
    lines.extend(["", f"### {guide_label}"])
    overview_texts = {_fact_key(fact.text) for fact in overview_facts}
    for node in summary.display_nodes:
        page_label = _page_label(node.page_start, node.page_end)
        lines.extend(["", f"#### {node.label}{page_label}"])
        node_facts = [fact for fact in node.facts if _fact_key(fact.text) not in overview_texts]
        if not node_facts:
            node_facts = list(node.facts)
        for fact in node_facts[:3]:
            lines.append(f"- {fact.text} [{anchor(fact)}]")

    return "\n".join(lines).strip(), cited_rows


def _build_section_nodes(rows: list[dict[str, object]]) -> list[SummaryNode]:
    grouped: list[tuple[str, str, list[dict[str, object]]]] = []
    for row in rows:
        key = _section_key(row)
        label = _section_label(row)
        if grouped and grouped[-1][0] == key:
            grouped[-1][2].append(row)
        else:
            grouped.append((key, label, [row]))

    return [
        _node_from_rows(
            label=label,
            kind="section",
            rows=section_rows,
            fact_limit=3,
        )
        for _, label, section_rows in grouped
    ]


def _build_chapter_nodes(sections: list[SummaryNode]) -> list[SummaryNode]:
    boundaries = _structure_boundaries(sections)
    if not boundaries:
        return sections

    groups: list[tuple[str, list[SummaryNode]]] = []
    current_label = "Front matter"
    current_children: list[SummaryNode] = []
    for index, section in enumerate(sections):
        if index in boundaries:
            if current_children:
                groups.append(
                    (_label_missing_chapter_range(current_label, section.label), current_children)
                )
            current_label = section.label
            current_children = [section]
        else:
            current_children.append(section)
    if current_children:
        groups.append((current_label, current_children))

    return [
        _node_from_children(label=label, kind="chapter", children=children, fact_limit=4)
        for label, children in groups
    ]


def _coalesce_for_display(nodes: list[SummaryNode], *, limit: int) -> list[SummaryNode]:
    current = nodes
    while len(current) > limit:
        group_size = max(2, math.ceil(len(current) / limit))
        current = [
            _node_from_children(
                label=_range_label(group),
                kind="region",
                children=group,
                fact_limit=3,
            )
            for group in _batches(current, group_size)
        ]
    return current


def _reduce_to_root(nodes: list[SummaryNode], *, fanout: int) -> tuple[SummaryNode, int]:
    current = nodes
    depth = 1
    while len(current) > fanout:
        current = [
            _node_from_children(
                label=_range_label(group),
                kind="region",
                children=group,
                fact_limit=4,
            )
            for group in _batches(current, fanout)
        ]
        depth += 1
    root = _node_from_children(
        label="Document",
        kind="document",
        children=current,
        fact_limit=5,
    )
    return root, depth + 1


def _node_from_rows(
    *,
    label: str,
    kind: str,
    rows: list[dict[str, object]],
    fact_limit: int,
) -> SummaryNode:
    facts = tuple(_select_row_facts(rows=rows, heading=label, limit=fact_limit))
    chunk_ids = tuple(str(row.get("id") or "") for row in rows if row.get("id"))
    page_start, page_end = _row_page_range(rows)
    return SummaryNode(
        node_id=_node_id(kind, label, chunk_ids),
        label=label,
        kind=kind,
        page_start=page_start,
        page_end=page_end,
        facts=facts,
        source_chunk_ids=chunk_ids,
    )


def _node_from_children(
    *,
    label: str,
    kind: str,
    children: list[SummaryNode],
    fact_limit: int,
) -> SummaryNode:
    facts = _select_child_facts(children=children, limit=fact_limit)
    chunk_ids = tuple(
        dict.fromkeys(chunk_id for child in children for chunk_id in child.source_chunk_ids)
    )
    starts = [child.page_start for child in children if child.page_start is not None]
    ends = [child.page_end for child in children if child.page_end is not None]
    return SummaryNode(
        node_id=_node_id(kind, label, chunk_ids),
        label=label,
        kind=kind,
        page_start=min(starts) if starts else None,
        page_end=max(ends) if ends else None,
        facts=tuple(facts),
        source_chunk_ids=chunk_ids,
        children=tuple(children),
    )


def _select_row_facts(
    *,
    rows: list[dict[str, object]],
    heading: str,
    limit: int,
) -> list[SummaryFact]:
    candidates: list[tuple[float, int, SummaryFact]] = []
    heading_terms = _terms(heading)
    all_units: list[tuple[int, int, str, dict[str, object]]] = []
    for row_index, row in enumerate(rows):
        row_text = _strip_repeated_heading(str(row.get("text") or ""), heading)
        if _looks_like_index_text(row_text):
            continue
        for unit_index, unit in enumerate(_text_units(row_text)):
            unit = _strip_repeated_heading(unit, heading)
            if len(unit.split()) < 6 or _low_value(unit):
                continue
            all_units.append((row_index, unit_index, unit, row))
    if not all_units:
        return []

    frequency = Counter(term for _, _, unit, _ in all_units for term in _terms(unit))
    peak = max(frequency.values(), default=1)
    for row_index, unit_index, unit, row in all_units:
        unit_terms = _terms(unit)
        centrality = sum(frequency[term] / peak for term in unit_terms) / max(len(unit_terms), 1)
        heading_overlap = len(unit_terms & heading_terms) / max(len(heading_terms), 1)
        category = _fact_category(unit)
        category_bonus = {
            "definition": 1.4,
            "method": 1.1,
            "result": 1.0,
            "limitation": 0.9,
            "equation": 1.0,
            "other": 0.0,
        }[category]
        word_count = len(unit.split())
        length_bonus = 0.6 if 10 <= word_count <= 48 else 0.15
        position_bonus = max(0.0, 0.8 - (row_index * 0.08) - (unit_index * 0.05))
        quality = float(row.get("quality_score") or 1.0)
        score = quality + centrality + (1.3 * heading_overlap) + category_bonus + length_bonus + position_bonus
        candidates.append(
            (
                score,
                len(candidates),
                SummaryFact(text=unit, source_row=row, score=round(score, 3), category=category),
            )
        )
    return _diverse_facts(candidates, limit=limit)


def _select_child_facts(*, children: list[SummaryNode], limit: int) -> list[SummaryFact]:
    if not children or limit <= 0:
        return []
    candidates: list[tuple[float, int, SummaryFact]] = []
    for child_index, child in enumerate(children):
        for fact_index, fact in enumerate(child.facts):
            coverage_bonus = 0.65 if fact_index == 0 else 0.25
            position_bonus = max(0.0, 0.35 - (child_index * 0.01))
            lead_bonus = 1.2 if child_index == 0 and fact_index == 0 else 0.0
            candidates.append(
                (fact.score + coverage_bonus + position_bonus + lead_bonus, child_index, fact)
            )

    selected: list[SummaryFact] = []
    used_children: set[int] = set()
    used_texts: list[str] = []
    for child_index, child in enumerate(children):
        if child.facts:
            selected.append(child.facts[0])
            used_children.add(child_index)
            used_texts.append(child.facts[0].text)
            break
    if len(selected) >= limit:
        return selected
    for score, child_index, fact in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if child_index in used_children or _duplicates(fact.text, used_texts):
            continue
        selected.append(fact)
        used_children.add(child_index)
        used_texts.append(fact.text)
        if len(selected) >= limit:
            return selected
    for _, _, fact in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if _duplicates(fact.text, used_texts):
            continue
        selected.append(fact)
        used_texts.append(fact.text)
        if len(selected) >= limit:
            break
    return selected


def _diverse_facts(
    candidates: list[tuple[float, int, SummaryFact]],
    *,
    limit: int,
) -> list[SummaryFact]:
    selected: list[SummaryFact] = []
    used_categories: set[str] = set()
    used_texts: list[str] = []
    ranked = sorted(candidates, key=lambda item: (-item[0], item[1]))
    for _, _, fact in ranked:
        if fact.category in used_categories or _duplicates(fact.text, used_texts):
            continue
        selected.append(fact)
        used_categories.add(fact.category)
        used_texts.append(fact.text)
        if len(selected) >= limit:
            return selected
    for _, _, fact in ranked:
        if _duplicates(fact.text, used_texts):
            continue
        selected.append(fact)
        used_texts.append(fact.text)
        if len(selected) >= limit:
            break
    return selected


def _text_units(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", _repair_display_text(text)).strip()
    if not normalized:
        return []
    rough = re.split(r"(?<=[.!?])\s+|\s+[|•]\s+|\s+(?=(?:First|Second|Finally)\b)", normalized)
    units: list[str] = []
    for item in rough:
        item = item.strip(" -|•")
        item = re.sub(r"^(?:\d+\s+){3,}", "", item).strip()
        if not item:
            continue
        words = item.split()
        if len(words) <= 58:
            units.append(item)
            continue
        for start in range(0, len(words), 46):
            window = words[start : start + 46]
            if len(window) >= 6:
                units.append(" ".join(window).strip())
    return units


def _strip_repeated_heading(text: str, heading: str) -> str:
    normalized_text = re.sub(r"\s+", " ", text).strip()
    normalized_heading = re.sub(r"\s+", " ", heading).strip(" .:-")
    if not normalized_heading:
        return normalized_text
    match = re.match(
        rf"^{re.escape(normalized_heading)}(?:\s*[:-]\s*|\s+)(?P<body>.+)$",
        normalized_text,
        re.IGNORECASE,
    )
    if not match:
        return normalized_text
    body = match.group("body").strip()
    return body if len(body.split()) >= 6 else normalized_text


def _is_readable(row: dict[str, object]) -> bool:
    text = re.sub(r"\s+", " ", str(row.get("text") or "")).strip()
    heading = str(row.get("section_path") or row.get("heading") or "")
    if _structured_heading(heading) and text.lower().startswith(heading.strip().lower()):
        return True
    if len(text.split()) < 6:
        return False
    lowered = text.lower()
    return not any(marker in lowered for marker in _LOW_VALUE_MARKERS)


def _low_value(text: str) -> bool:
    lowered = text.lower()
    if any(marker in lowered for marker in _LOW_VALUE_MARKERS):
        return True
    if lowered.startswith(("references ", "bibliography ")):
        return True
    code_markers = len(
        re.findall(
            r"\b[A-Za-z_]\w*\([^)]*\)|\b(?:from|import)\s+[A-Za-z_]|\b[A-Za-z_]\w*\s*=",
            text,
        )
    )
    if code_markers >= 2 and not re.search(
        r"\b(?:equation|formula|calculated as)\b",
        lowered,
    ):
        return True
    if (
        len(text.split()) <= 20
        and re.search(r"\b[A-Za-z_]\w*\s*=", text)
        and not re.search(r"\b(?:equation|formula|calculated as)\b", lowered)
    ):
        return True
    comma_fragments = [part for part in re.split(r"[,;]", text) if part.strip()]
    sentence_endings = len(re.findall(r"[.!?](?:\s|$)", text))
    return len(comma_fragments) >= 6 and sentence_endings <= 1


def _looks_like_index_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", _repair_display_text(text)).strip()
    if len(normalized.split()) < 20:
        return False
    comma_fragments = [part for part in re.split(r"[,;]", normalized) if part.strip()]
    sentence_endings = len(re.findall(r"[.!?](?:\s|$)", normalized))
    return len(comma_fragments) >= 7 and sentence_endings <= 2


def _exclude_late_index_region(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    minimum_index = int(len(rows) * 0.72)
    for index, row in enumerate(rows):
        if index < minimum_index:
            continue
        if not _looks_like_index_text(str(row.get("text") or "")):
            continue
        window = rows[index : index + 12]
        dense_rows = sum(
            _looks_like_index_text(str(candidate.get("text") or "")) for candidate in window
        )
        if dense_rows >= 4:
            return rows[:index], len(rows) - index
    return rows, 0


def _fact_category(text: str) -> str:
    lowered = f" {text.lower()} "
    if re.search(r"\b(?:is a|is an|refers to|defined as|means|consists of)\b", lowered):
        return "definition"
    if re.search(r"\b(?:equation|formula|calculated as)\b", lowered) or re.search(
        r"\b[A-Za-z][A-Za-z0-9_]*\s*=\s*[^,.;]+", text
    ):
        return "equation"
    if re.search(r"\b(?:first|then|next|finally|method|procedure|algorithm|step)\b", lowered):
        return "method"
    if re.search(r"\b(?:result|found|achieved|improved|increased|decreased|shows that)\b", lowered):
        return "result"
    if re.search(r"\b(?:limitation|however|although|caveat|fails|cannot|does not)\b", lowered):
        return "limitation"
    return "other"


def _duplicates(candidate: str, selected: list[str]) -> bool:
    candidate_terms = _terms(candidate)
    candidate_key = _fact_key(candidate)
    for existing in selected:
        if candidate_key == _fact_key(existing):
            return True
        existing_terms = _terms(existing)
        union = candidate_terms | existing_terms
        if union and len(candidate_terms & existing_terms) / len(union) >= 0.82:
            return True
    return False


def _row_order(row: dict[str, object]) -> tuple[int, int, str]:
    return (
        int(row.get("chunk_index") if row.get("chunk_index") is not None else 1_000_000),
        int(row.get("page_start") or 1_000_000),
        str(row.get("id") or ""),
    )


def _section_key(row: dict[str, object]) -> str:
    return str(
        row.get("section_id")
        or row.get("section_path")
        or row.get("heading")
        or f"page-{row.get('page_start') or 'unknown'}"
    )


def _section_label(row: dict[str, object]) -> str:
    value = str(row.get("section_path") or row.get("heading") or "").strip(" /.-")
    value = _repair_display_text(value)
    return re.sub(r"\s+", " ", value)[:180] or f"Page {row.get('page_start') or '?'}"


def _is_chapter_heading(label: str) -> bool:
    return _structured_heading(label) is not None


def _structure_boundaries(sections: list[SummaryNode]) -> set[int]:
    boundaries: set[int] = set()
    last_ordinals: dict[str, int] = {}
    for index, section in enumerate(sections):
        parsed = _structured_heading(section.label)
        if not parsed:
            continue
        kind, ordinal = parsed
        if kind == "part":
            continue
        previous = last_ordinals.get(kind)
        if previous is not None and ordinal <= previous:
            continue
        boundaries.add(index)
        last_ordinals[kind] = ordinal
    return boundaries


def _label_missing_chapter_range(current_label: str, next_label: str) -> str:
    current = _structured_heading(current_label)
    following = _structured_heading(next_label)
    if not current or not following:
        return current_label
    current_kind, current_ordinal = current
    next_kind, next_ordinal = following
    if current_kind != "chapter" or next_kind != "chapter" or next_ordinal <= current_ordinal + 1:
        return current_label
    missing_start = current_ordinal + 1
    missing_end = next_ordinal - 1
    missing = (
        f"Chapter {missing_start}"
        if missing_start == missing_end
        else f"Chapters {missing_start}-{missing_end}"
    )
    return f"{current_label} + {missing} (heading unavailable)"


def _structured_heading(label: str) -> tuple[str, int] | None:
    normalized = re.sub(r"\s+", " ", _repair_display_text(label)).strip()
    if len(normalized) > 140 or "?" in normalized:
        return None
    match = re.match(
        r"^(?P<kind>(?i:part|chapter|unit|module|appendix))\s+"
        r"(?P<number>\d{1,2}|[IVXLCDMivxlcdm]{1,6}|[A-Z])"
        r"(?:\s*[.:-]\s*|\s+)(?P<title>[A-Z][^=()]{1,100})$",
        normalized,
    )
    if not match or len(match.group("title").split()) > 16:
        return None
    kind = match.group("kind").lower()
    number = match.group("number")
    ordinal = _heading_ordinal(number, alphabetic=kind == "appendix")
    if ordinal is None:
        return None
    if kind in {"chapter", "unit", "module"}:
        kind = "chapter"
    return kind, ordinal


def _heading_ordinal(value: str, *, alphabetic: bool = False) -> int | None:
    if value.isdigit():
        return int(value)
    if len(value) == 1 and value.isalpha() and (alphabetic or value.upper() not in "IVXLCDM"):
        return ord(value.upper()) - ord("A") + 1
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for character in reversed(value.upper()):
        current = values.get(character)
        if current is None:
            return None
        total += -current if current < previous else current
        previous = max(previous, current)
    return total or None


def _repair_display_text(text: str) -> str:
    def repair_run(match: re.Match[str]) -> str:
        value = match.group(0)
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value

    text = re.sub(r"[\x80-\xff]{2,}", repair_run, text)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "â": "'",
        "â": "'",
        "â": '"',
        "â": '"',
        "â": "-",
        "â": "-",
        "â": " approximately ",
        "â": "-",
        "Î±": "alpha",
        "Î²": "beta",
        "Î³": "gamma",
        "Îµ": "epsilon",
        "Î¶": "zeta",
        "Â": "",
    }
    repaired = text
    for damaged, replacement in replacements.items():
        repaired = repaired.replace(damaged, replacement)
    return repaired


def _range_label(nodes: list[SummaryNode]) -> str:
    if not nodes:
        return "Document region"
    if len(nodes) == 1:
        return nodes[0].label
    return f"{nodes[0].label} to {nodes[-1].label}"


def _progressive_overview_facts(summary: RecursiveSummary) -> list[SummaryFact]:
    available = [node.facts[0] for node in summary.display_nodes if node.facts]
    if not available:
        return list(summary.root.facts[:4])
    positions = [0, len(available) // 3, (2 * len(available)) // 3, len(available) - 1]
    selected: list[SummaryFact] = []
    used: list[str] = []
    for position in positions:
        fact = available[min(position, len(available) - 1)]
        if _duplicates(fact.text, used):
            continue
        selected.append(fact)
        used.append(fact.text)
    return selected or list(summary.root.facts[:4])


def _node_id(kind: str, label: str, source_chunk_ids: tuple[str, ...]) -> str:
    digest = hashlib.sha1(
        f"{kind}|{label}|{'|'.join(source_chunk_ids)}".encode("utf-8")
    ).hexdigest()[:20]
    return f"sum_{digest}"


def _row_page_range(rows: list[dict[str, object]]) -> tuple[int | None, int | None]:
    starts = [int(row["page_start"]) for row in rows if row.get("page_start") is not None]
    ends = [int(row["page_end"]) for row in rows if row.get("page_end") is not None]
    return (min(starts) if starts else None, max(ends) if ends else None)


def _page_label(page_start: int | None, page_end: int | None) -> str:
    if page_start is None:
        return ""
    if page_end is None or page_end == page_start:
        return f" (p. {page_start})"
    return f" (pp. {page_start}-{page_end})"


def _terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text.lower())
        if token not in _STOPWORDS
    }


def _fact_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())[:240]


def _batches(items: list[SummaryNode], size: int) -> list[list[SummaryNode]]:
    return [items[start : start + size] for start in range(0, len(items), size)]
