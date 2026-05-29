from dataclasses import dataclass


@dataclass(slots=True)
class RetrievalPolicy:
    bm25_k: int = 20
    vector_k: int = 20
    fused_k: int = 24
    rerank_k: int = 8
    rrf_k: int = 60
    max_chunks_per_document: int = 2
    max_context_tokens: int = 2400
    min_grounding_score: float = 0.15
