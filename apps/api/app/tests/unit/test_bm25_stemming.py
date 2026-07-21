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


def test_bm25_search_many_matches_individual_searches() -> None:
    index = BM25Index()
    chunks = [
        {
            "id": "definition",
            "document_id": "doc",
            "text": "A model is a compact representation of patterns in data.",
            "page_start": 1,
            "page_end": 1,
        },
        {
            "id": "operation",
            "document_id": "doc",
            "text": "Training updates model parameters to reduce prediction error.",
            "page_start": 2,
            "page_end": 2,
        },
    ]
    queries = {
        "identity": "model definition representation",
        "operation": "training updates parameters",
    }

    batched = asyncio.run(index.search_many(queries=queries, chunks=chunks, limit=2))
    individual = {
        key: asyncio.run(index.search(query, chunks, limit=2))
        for key, query in queries.items()
    }

    assert {
        key: [(hit.chunk_id, hit.score) for hit in hits]
        for key, hits in batched.items()
    } == {
        key: [(hit.chunk_id, hit.score) for hit in hits]
        for key, hits in individual.items()
    }


def test_bm25_reuses_tokenized_corpus_for_same_chunks() -> None:
    index = BM25Index()
    chunks = [
        {
            "id": "chunk-1",
            "document_id": "doc",
            "chunk_hash": "hash-a",
            "text": "Gaussian mixture models represent data using several Gaussian distributions.",
            "page_start": 1,
            "page_end": 1,
        }
    ]

    first = asyncio.run(index.search("Gaussian mixture", chunks, limit=1))
    assert first[0].chunk_id == "chunk-1"
    assert index.last_cache_hit is False

    second = asyncio.run(index.search("Gaussian distributions", chunks, limit=1))

    assert second[0].chunk_id == "chunk-1"
    assert index.last_cache_hit is True
    assert index.stats()["cache_hits"] == 1
    assert index.stats()["cache_misses"] == 1


def test_bm25_cache_invalidates_when_chunk_hash_changes() -> None:
    index = BM25Index()
    original = [
        {
            "id": "chunk-1",
            "document_id": "doc",
            "chunk_hash": "hash-a",
            "text": "The old passage explains clustering.",
            "page_start": 1,
            "page_end": 1,
        }
    ]
    changed = [
        {
            "id": "chunk-1",
            "document_id": "doc",
            "chunk_hash": "hash-b",
            "text": "The new passage explains convolutional networks.",
            "page_start": 1,
            "page_end": 1,
        }
    ]

    assert asyncio.run(index.search("clustering", original, limit=1))[0].chunk_id == "chunk-1"
    assert index.last_cache_hit is False

    hits = asyncio.run(index.search("convolutional networks", changed, limit=1))

    assert hits[0].chunk_id == "chunk-1"
    assert index.last_cache_hit is False
    assert index.stats()["cache_misses"] == 2
