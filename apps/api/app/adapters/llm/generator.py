from app.adapters.llm.ollama_client import OllamaClient


class Generator:
    """Generator with Ollama path and deterministic offline fallback."""

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        default_model: str = "phi3:mini",
        use_ollama: bool = True,
    ) -> None:
        self._ollama_client = ollama_client
        self._default_model = default_model
        self._use_ollama = use_ollama
        self.last_backend = "fallback"

    async def answer(self, prompt: str, model: str | None = None) -> str:
        target_model = model or self._default_model
        if self._use_ollama and self._ollama_client and await self._ollama_client.is_available():
            try:
                response = await self._ollama_client.generate(
                    prompt=prompt,
                    model=target_model,
                    temperature=0.1,
                )
                if response.strip():
                    self.last_backend = "ollama"
                    return response.strip()
            except Exception:
                pass
        self.last_backend = "fallback"
        return ""
