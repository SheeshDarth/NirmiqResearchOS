import asyncio

from app.adapters.retrieval.bm25_index import BM25Index


def test_bm25_matches_light_morphology_variants() -> None:
    chunks = [
        {
            "id": "definition",
            "document_id": "doc",
            "text": "Overfitting means the model performs well on training data but does not generalize well.",
            "page_start": 58,
            "page_end": 58,
        },
        {
            "id": "solution",
            "document_id": "doc",
            "text": "A possible solution is to simplify the model and reduce noise in the training data.",
            "page_start": 59,
            "page_end": 59,
        },
    ]

    hits = asyncio.run(BM25Index().search("How can overfit be reduced?", chunks, limit=2))

    assert {hit.chunk_id for hit in hits} == {"solution", "definition"}
