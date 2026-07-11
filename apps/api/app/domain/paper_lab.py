import re
from collections import Counter

from app.domain.models import RetrievedChunk


def build_paper_lab_artifact(chunks: list[RetrievedChunk]) -> dict[str, object]:
    useful_chunks = _select_diverse_chunks([chunk for chunk in chunks if chunk.text.strip()], limit=8)
    clusters: dict[str, list[dict[str, object]]] = {}
    matrix: list[dict[str, object]] = []

    for index, chunk in enumerate(useful_chunks, start=1):
        role = _evidence_role(chunk.text)
        excerpt = _best_excerpt(chunk.text)
        clusters.setdefault(role, []).append(
            {
                "evidence": index,
                "document_id": chunk.document_id,
                "page": chunk.page_start,
                "score": round(chunk.score, 3),
                "excerpt": excerpt,
            }
        )
        matrix.append(
            {
                "claim_area": role.replace("_", " ").title(),
                "evidence": index,
                "page": chunk.page_start,
                "source_type": chunk.source,
                "quality": round(chunk.quality_score, 3),
                "use_in_paper": _paper_usage(role),
                "excerpt": excerpt,
            }
        )

    return {
        "source_count": len({chunk.document_id for chunk in useful_chunks}),
        "evidence_count": len(useful_chunks),
        "source_diversity": _source_diversity(useful_chunks),
        "guardrails": _academic_guardrails(useful_chunks),
        "section_templates": _section_templates(),
        "citation_clusters": clusters,
        "related_work_matrix": matrix,
        "outline": [
            "Title and problem framing",
            "Background and related work",
            "Methodology or system design",
            "Evidence-backed discussion",
            "Limitations and future work",
        ],
    }


def _select_diverse_chunks(chunks: list[RetrievedChunk], *, limit: int) -> list[RetrievedChunk]:
    source_count = len({chunk.document_id for chunk in chunks})
    if source_count <= 1:
        return chunks[:limit]

    selected: list[RetrievedChunk] = []
    seen_chunk_ids: set[str] = set()
    per_document: Counter[str] = Counter()
    max_per_document = max(2, limit // source_count)

    for chunk in chunks:
        if len(selected) >= limit:
            break
        if chunk.chunk_id in seen_chunk_ids:
            continue
        if per_document[chunk.document_id] >= max_per_document:
            continue
        selected.append(chunk)
        seen_chunk_ids.add(chunk.chunk_id)
        per_document[chunk.document_id] += 1

    return selected or chunks[:limit]


def _source_diversity(chunks: list[RetrievedChunk]) -> dict[str, object]:
    if not chunks:
        return {
            "unique_documents": 0,
            "dominant_document_share": 0.0,
            "status": "no_evidence",
        }
    counts = Counter(chunk.document_id for chunk in chunks)
    dominant_share = max(counts.values()) / len(chunks)
    status = "balanced"
    if len(counts) == 1:
        status = "single_source"
    elif dominant_share >= 0.75:
        status = "dominant_source"
    return {
        "unique_documents": len(counts),
        "dominant_document_share": round(dominant_share, 3),
        "status": status,
    }


def _academic_guardrails(chunks: list[RetrievedChunk]) -> list[str]:
    guardrails = [
        "Use only claims supported by retrieved source excerpts.",
        "Place citations at paragraph or bullet level where source evidence is used.",
        "Add a limitation note when evidence is narrow, single-source, or indirect.",
        "Do not invent papers, authors, results, diagrams, or references not present in the corpus.",
    ]
    diversity = _source_diversity(chunks)
    if not chunks:
        guardrails.append("Not enough retrieved evidence is available for a safe academic draft.")
    elif diversity["status"] == "single_source":
        guardrails.append("Evidence currently comes from one source; avoid broad literature claims.")
    elif diversity["status"] == "dominant_source":
        guardrails.append("One source dominates the evidence; use comparison language carefully.")
    return guardrails


def _section_templates() -> dict[str, list[str]]:
    return {
        "problem_statement": [
            "State the problem in one paragraph.",
            "Cite the source sentence that proves the problem exists.",
            "Avoid claims about market size, novelty, or impact unless retrieved evidence supports them.",
        ],
        "related_work": [
            "Compare retrieved source claims instead of listing them.",
            "Use source-diversity notes to avoid overclaiming from one document.",
            "End with the gap that the retrieved evidence actually supports.",
        ],
        "methodology": [
            "Describe the method or system design from retrieved evidence.",
            "Separate implementation details from assumptions.",
            "Cite each technical claim that depends on the source.",
        ],
        "limitations": [
            "Mention limitations only when supported by source evidence or by explicit evidence gaps.",
            "Do not invent experimental failures or future work.",
            "State missing evidence plainly when the corpus is incomplete.",
        ],
    }


def _evidence_role(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(limitations?|future work|challenge|caveat|fail|weakness)\b", lowered):
        return "limitations"
    if re.search(r"\b(method|methodology|architecture|design|algorithm|system)\b", lowered):
        return "methodology"
    if re.search(r"\b(result|accuracy|performance|evaluation|experiment|score)\b", lowered):
        return "results"
    if re.search(r"\b(previous|related|prior|literature|baseline|compare)\b", lowered):
        return "related_work"
    return "background"


def _paper_usage(role: str) -> str:
    return {
        "background": "Use for context or motivation.",
        "related_work": "Use in related-work comparison.",
        "methodology": "Use for method/design explanation.",
        "results": "Use to support findings or evaluation.",
        "limitations": "Use for limitations/future-work section.",
    }.get(role, "Use as supporting evidence.")


def _best_excerpt(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    sentences = [
        sentence.strip(" -")
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if len(sentence.split()) >= 7
    ]
    excerpt = sentences[0] if sentences else normalized
    return excerpt[:260].strip()
