from app.api.schemas.common import Citation
from app.domain.models import RetrievedChunk


def to_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            score=chunk.score,
            excerpt=_build_excerpt(chunk.text),
        )
        for chunk in chunks
    ]


def _build_excerpt(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."
