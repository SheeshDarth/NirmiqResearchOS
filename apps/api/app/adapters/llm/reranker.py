from app.adapters.llm.ollama_client import OllamaClient


class Reranker:
    """Reranker with Ollama relevance scoring + lexical fallback."""

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        model_name: str = "bge-reranker-base",
        use_ollama: bool = True,
        max_model_items: int = 8,
    ) -> None:
        self._ollama_client = ollama_client
        self._model_name = model_name
        self._use_ollama = use_ollama
        self._max_model_items = max_model_items
        self.last_backend = "lexical"

    async def rerank(self, query: str, texts: list[str]) -> list[int]:
        if (
            self._use_ollama
            and self._ollama_client
            and texts
            and await self._ollama_client.is_available()
        ):
            order = await self._rerank_with_ollama(query=query, texts=texts)
            if order:
                self.last_backend = "ollama"
                return order

        self.last_backend = "lexical"
        return self._rerank_lexical(query=query, texts=texts)

    async def _rerank_with_ollama(self, query: str, texts: list[str]) -> list[int]:
        scored_limit = min(self._max_model_items, len(texts))
        candidate_texts = texts[:scored_limit]
        try:
            scores = await self._ollama_client.relevance_scores(
                query=query,
                texts=candidate_texts,
                model=self._model_name,
            )
        except Exception:
            return []
        if len(scores) != scored_limit:
            return []

        pairs = [(idx, float(score)) for idx, score in enumerate(scores)]
        pairs.sort(key=lambda item: item[1], reverse=True)
        model_ranked = [idx for idx, _ in pairs]
        tail = list(range(scored_limit, len(texts)))
        return model_ranked + tail

    def _rerank_lexical(self, query: str, texts: list[str]) -> list[int]:
        query_tokens = self._tokenize(query)
        if not texts or not query_tokens:
            return list(range(len(texts)))

        scores: list[tuple[int, float]] = []
        query_set = set(query_tokens)
        for idx, text in enumerate(texts):
            tokens = self._tokenize(text)
            if not tokens:
                scores.append((idx, 0.0))
                continue
            overlap = len(query_set.intersection(tokens))
            density = overlap / max(len(set(tokens)), 1)
            position_bias = 1.0 / (idx + 1)
            score = (0.8 * density) + (0.2 * position_bias)
            scores.append((idx, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return [idx for idx, _ in scores]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        sanitized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
        return [token for token in sanitized.split() if token]
