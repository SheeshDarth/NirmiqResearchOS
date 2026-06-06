from dataclasses import dataclass, field


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_start: int | None = None
    page_end: int | None = None
    source: str = "hybrid"
    quality_score: float = 1.0


@dataclass(slots=True)
class RetrievalBundle:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)
