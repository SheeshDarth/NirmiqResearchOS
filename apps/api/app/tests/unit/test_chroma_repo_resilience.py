import asyncio
from pathlib import Path

from app.adapters.storage.chroma_repo import ChromaRepo


class DimensionMismatchCollection:
    def __init__(self) -> None:
        self.calls = 0

    def upsert(self, **_: object) -> None:
        self.calls += 1
        raise ValueError("Collection expecting embedding with dimension of 768, got 256")


class HealthyCollection:
    def __init__(self) -> None:
        self.upserted = False

    def upsert(self, **_: object) -> None:
        self.upserted = True


class FakeClient:
    def __init__(self, healthy: HealthyCollection) -> None:
        self.healthy = healthy
        self.deleted = False

    def delete_collection(self, name: str) -> None:
        assert name == "chunks_v1"
        self.deleted = True

    def get_or_create_collection(self, name: str) -> HealthyCollection:
        assert name == "chunks_v1"
        return self.healthy


def test_chroma_upsert_recovers_from_embedding_dimension_mismatch(tmp_path: Path) -> None:
    repo = ChromaRepo(tmp_path)
    failing = DimensionMismatchCollection()
    healthy = HealthyCollection()
    client = FakeClient(healthy)
    repo._ready = True
    repo._collection = failing
    repo._client = client

    asyncio.run(
        repo.upsert_chunks(
            chunks=[
                {
                    "id": "chunk-1",
                    "document_id": "doc-1",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "NIRMIQ test chunk.",
                    "quality_score": 1.0,
                }
            ],
            embeddings=[[0.1, 0.2, 0.3]],
        )
    )

    assert failing.calls == 1
    assert client.deleted is True
    assert healthy.upserted is True


def test_chroma_dimension_error_detection() -> None:
    assert ChromaRepo._is_dimension_error(
        ValueError("Collection expecting embedding with dimension of 768, got 256")
    )
    assert not ChromaRepo._is_dimension_error(ValueError("network unavailable"))
