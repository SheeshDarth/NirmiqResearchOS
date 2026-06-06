from pathlib import Path
from typing import Any


class ChromaRepo:
    """Optional ChromaDB adapter with graceful fallback when chromadb is unavailable."""

    def __init__(self, persist_path: Path, collection_name: str = "chunks_v1") -> None:
        self._persist_path = persist_path
        self._collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None
        self._ready = False
        self._init_error: str | None = None
        self._persist_path.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        self._ensure_collection()
        return self._ready

    def last_error(self) -> str | None:
        return self._init_error

    async def delete_document(self, document_id: str) -> None:
        if not self.is_available():
            return
        assert self._collection is not None
        try:
            self._collection.delete(where={"document_id": document_id})
        except Exception as exc:
            if self._is_dimension_error(exc):
                self._reset_collection()
                return
            raise

    async def upsert_chunks(self, chunks: list[dict[str, object]], embeddings: list[list[float]]) -> None:
        if not chunks or not embeddings or len(chunks) != len(embeddings):
            return
        if not self.is_available():
            return
        assert self._collection is not None
        ids = [str(chunk["id"]) for chunk in chunks]
        documents = [str(chunk["text"]) for chunk in chunks]
        metadatas = [
            {
                "document_id": str(chunk["document_id"]),
                "page_start": int(chunk["page_start"]) if chunk["page_start"] is not None else -1,
                "page_end": int(chunk["page_end"]) if chunk["page_end"] is not None else -1,
                "quality_score": float(chunk.get("quality_score", 1.0)),
            }
            for chunk in chunks
        ]
        try:
            self._collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        except Exception as exc:
            if not self._is_dimension_error(exc):
                raise
            self._reset_collection()
            if not self.is_available():
                return
            assert self._collection is not None
            self._collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    async def query(
        self, query_embedding: list[float], limit: int, document_id: str | None = None
    ) -> list[dict[str, object]]:
        if not query_embedding or limit <= 0:
            return []
        if not self.is_available():
            return []
        assert self._collection is not None
        query_kwargs: dict[str, object] = {
            "query_embeddings": [query_embedding],
            "n_results": limit,
            "include": ["distances", "documents", "metadatas"],
        }
        if document_id:
            query_kwargs["where"] = {"document_id": document_id}
        try:
            result = self._collection.query(**query_kwargs)
        except Exception as exc:
            if self._is_dimension_error(exc):
                return []
            raise
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        hits: list[dict[str, object]] = []
        for idx, chunk_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            score = 1.0 / (1.0 + max(distance, 0.0))
            page_start_raw = metadata.get("page_start") if isinstance(metadata, dict) else None
            page_end_raw = metadata.get("page_end") if isinstance(metadata, dict) else None
            quality_score_raw = metadata.get("quality_score") if isinstance(metadata, dict) else 1.0
            hits.append(
                {
                    "id": chunk_id,
                    "document_id": metadata.get("document_id") if isinstance(metadata, dict) else None,
                    "page_start": page_start_raw if page_start_raw != -1 else None,
                    "page_end": page_end_raw if page_end_raw != -1 else None,
                    "text": documents[idx] if idx < len(documents) else "",
                    "score": score,
                    "quality_score": quality_score_raw,
                }
            )
        return hits

    def _ensure_collection(self) -> None:
        if self._ready:
            return
        if self._init_error:
            return
        try:
            import chromadb  # type: ignore
        except Exception as exc:
            self._init_error = str(exc)
            return

        try:
            self._client = chromadb.PersistentClient(path=str(self._persist_path))
            self._collection = self._client.get_or_create_collection(name=self._collection_name)
            self._ready = True
        except Exception as exc:
            self._init_error = str(exc)

    def _reset_collection(self) -> None:
        if self._client is None:
            self._ready = False
            self._collection = None
            self._init_error = None
            self._ensure_collection()
            return
        try:
            self._client.delete_collection(name=self._collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(name=self._collection_name)
        self._ready = True
        self._init_error = None

    @staticmethod
    def _is_dimension_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "dimension" in message and ("embedding" in message or "collection" in message)
