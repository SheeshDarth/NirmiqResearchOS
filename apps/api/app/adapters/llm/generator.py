from app.adapters.llm.ollama_client import OllamaClient


class Generator:
    """Generator with Ollama path and deterministic offline fallback."""

    _preferred_generation_models = (
        "qwen3.5:4b",
        "phi3:mini",
        "llama3.2:3b",
        "gemma2:2b",
        "mistral:7b-instruct-q4_K_M",
        "deepseek-r1:8b",
        "deepseek-coder:6.7b",
    )
    _non_generation_model_terms = ("embed", "rerank", "nomic", "bge")
    _explicit_only_model_terms = ("qwen2.5",)

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
        self.last_model_requested = default_model
        self.last_model_used: str | None = None
        self.last_model_fallback = False
        self.last_error: str | None = None

    async def answer(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        target_model = model or self._default_model
        self.last_model_requested = target_model
        self.last_model_used = None
        self.last_model_fallback = False
        self.last_error = None
        if self._use_ollama and self._ollama_client and await self._ollama_client.is_available():
            try:
                resolved_model = await self._resolve_generation_model(target_model)
                self.last_model_used = resolved_model
                self.last_model_fallback = resolved_model != target_model
                response = await self._ollama_client.generate(
                    prompt=prompt,
                    model=resolved_model,
                    temperature=temperature,
                )
                if response.strip():
                    self.last_backend = "ollama"
                    return response.strip()
            except Exception as exc:
                self.last_error = (str(exc) or exc.__class__.__name__)[:240]
        self.last_backend = "fallback"
        return ""

    async def _resolve_generation_model(self, requested_model: str) -> str:
        if not self._ollama_client:
            return requested_model
        installed_models = await self._ollama_client.list_models()
        if not installed_models or requested_model in installed_models:
            return requested_model

        installed_by_lower = {model.lower(): model for model in installed_models}
        for preferred in self._preferred_generation_models:
            if preferred.lower() in installed_by_lower:
                return installed_by_lower[preferred.lower()]

        requested_family = requested_model.split(":", 1)[0].lower()
        for installed in installed_models:
            if installed.split(":", 1)[0].lower() == requested_family:
                return installed

        for installed in installed_models:
            lowered = installed.lower()
            if (
                not any(term in lowered for term in self._non_generation_model_terms)
                and not any(term in lowered for term in self._explicit_only_model_terms)
            ):
                return installed
        return requested_model
