import hashlib
import math

from app.adapters.llm.ollama_client import OllamaClient


class Embedder:
    """
    Deterministic hash embedding fallback.
    Keeps vector retrieval available offline without model runtime coupling.
    """

    def __init__(
        self,
        dim: int = 256,
        ollama_client: OllamaClient | None = None,
        model_name: str = "nomic-embed-text",
        use_ollama: bool = True,
        batch_size: int = 8,
    ) -> None:
        self._dim = dim
        self._ollama_client = ollama_client
        self._model_name = model_name
        self._use_ollama = use_ollama
        self._batch_size = max(1, batch_size)
        self.last_backend = "hash"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._use_ollama and self._ollama_client and await self._ollama_client.is_available():
            try:
                vectors: list[list[float]] = []
                for start in range(0, len(texts), self._batch_size):
                    batch = texts[start : start + self._batch_size]
                    vectors.extend(await self._ollama_client.embed(texts=batch, model=self._model_name))
                if len(vectors) == len(texts) and all(vectors):
                    self.last_backend = "ollama"
                    return [self._normalize(vector) for vector in vectors]
            except Exception:
                pass
        self.last_backend = "hash"
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        tokens = self._tokenize(text)
        if not tokens:
            return vector
        for token in tokens:
            index = self._hash_to_index(token)
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 1e-12:
            return vector
        return [value / norm for value in vector]

    def _hash_to_index(self, token: str) -> int:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        num = int.from_bytes(digest[:4], byteorder="big", signed=False)
        return num % self._dim

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        sanitized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
        return [token for token in sanitized.split() if token]

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 1e-12:
            return vector
        return [value / norm for value in vector]
