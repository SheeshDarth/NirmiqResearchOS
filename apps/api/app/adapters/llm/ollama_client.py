import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class OllamaClient:
    """Local Ollama API adapter with lightweight health caching."""

    def __init__(self, base_url: str, timeout_seconds: float = 4.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._health_cache_ttl = timedelta(seconds=10)
        self._last_health_check: datetime | None = None
        self._last_health_result = False

    async def is_available(self) -> bool:
        now = datetime.now(timezone.utc)
        if (
            self._last_health_check is not None
            and now - self._last_health_check < self._health_cache_ttl
        ):
            return self._last_health_result
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                self._last_health_result = response.status_code == 200
        except Exception:
            self._last_health_result = False
        self._last_health_check = now
        return self._last_health_result

    async def generate(self, prompt: str, model: str, temperature: float = 0.0) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        response = await self._post_json("/api/generate", payload)
        return str(response.get("response", ""))

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        if not texts:
            return []
        # Prefer batch embed endpoint when available.
        payload = {"model": model, "input": texts}
        try:
            response = await self._post_json("/api/embed", payload)
            embeddings = response.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                return [[float(value) for value in vector] for vector in embeddings]
        except Exception:
            # Fallback to per-text legacy embeddings endpoint.
            pass

        vectors: list[list[float]] = []
        for text in texts:
            legacy_payload = {"model": model, "prompt": text}
            response = await self._post_json("/api/embeddings", legacy_payload)
            vector = response.get("embedding", [])
            vectors.append([float(value) for value in vector])
        return vectors

    async def relevance_scores(self, query: str, texts: list[str], model: str) -> list[float]:
        scores: list[float] = []
        for text in texts:
            prompt = self._rerank_prompt(query, text)
            raw = await self.generate(prompt=prompt, model=model, temperature=0.0)
            scores.append(self._parse_score(raw))
        return scores

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(f"{self._base_url}{path}", json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected non-object response from Ollama")
            return data

    @staticmethod
    def _rerank_prompt(query: str, text: str) -> str:
        return (
            "You are a relevance scorer.\n"
            "Score how relevant DOCUMENT is to QUERY from 0 to 1.\n"
            "Return strict JSON only: {\"score\": number}\n\n"
            f"QUERY:\n{query}\n\nDOCUMENT:\n{text[:1800]}"
        )

    @staticmethod
    def _parse_score(raw: str) -> float:
        try:
            payload = json.loads(raw.strip())
            value = float(payload.get("score", 0.0))
            return max(0.0, min(1.0, value))
        except Exception:
            return 0.0
