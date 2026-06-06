import re

from app.domain.models import RetrievedChunk


def build_paper_lab_artifact(chunks: list[RetrievedChunk]) -> dict[str, object]:
    useful_chunks = [chunk for chunk in chunks if chunk.text.strip()][:8]
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
