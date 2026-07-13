import pytest

from app.core.config import Settings
from app.core.runtime_profiles import resolve_runtime_profile


PROFILE_ENV_KEYS = (
    "GENERATOR_MODEL_DEFAULT",
    "LOW_MEMORY_MODE",
    "USE_OLLAMA_GENERATION",
    "USE_OLLAMA_EMBEDDINGS",
    "USE_OLLAMA_RERANKER",
    "OLLAMA_KEEP_ALIVE",
    "OLLAMA_NUM_CTX",
    "OLLAMA_NUM_PREDICT",
    "OLLAMA_EMBED_BATCH_SIZE",
    "RETRIEVAL_ENABLE_VECTOR",
    "RETRIEVAL_MAX_CONTEXT_TOKENS",
)


def _clear_profile_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in PROFILE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_auto_profile_uses_low_memory_defaults_below_twelve_gib() -> None:
    profile = resolve_runtime_profile("auto", total_memory_bytes=8 * 1024**3)

    assert profile.name == "low_memory"
    assert profile.generator_model_default == "phi3:mini"
    assert profile.ollama_num_ctx == 2048
    assert profile.retrieval_enable_vector is False


def test_auto_profile_uses_balanced_defaults_at_twelve_gib_or_more() -> None:
    profile = resolve_runtime_profile("auto", total_memory_bytes=16 * 1024**3)

    assert profile.name == "balanced"
    assert profile.generator_model_default == "qwen3.5:4b"
    assert profile.ollama_num_ctx == 3072
    assert profile.retrieval_enable_vector is True


def test_cpu_offline_profile_disables_optional_model_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_profile_overrides(monkeypatch)
    monkeypatch.setenv("NIRMIQ_RUNTIME_PROFILE", "cpu-offline")

    settings = Settings.from_env()

    assert settings.runtime_profile == "cpu_offline"
    assert settings.use_ollama_generation is False
    assert settings.use_ollama_embeddings is False
    assert settings.use_ollama_reranker is False
    assert settings.retrieval_enable_vector is False
    assert settings.ollama_keep_alive == "0s"


def test_explicit_environment_values_override_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_profile_overrides(monkeypatch)
    monkeypatch.setenv("NIRMIQ_RUNTIME_PROFILE", "low_memory")
    monkeypatch.setenv("USE_OLLAMA_EMBEDDINGS", "true")
    monkeypatch.setenv("RETRIEVAL_ENABLE_VECTOR", "true")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "2560")
    monkeypatch.setenv("GENERATOR_MODEL_DEFAULT", "custom:3b")

    settings = Settings.from_env()

    assert settings.runtime_profile == "low_memory"
    assert settings.use_ollama_embeddings is True
    assert settings.retrieval_enable_vector is True
    assert settings.ollama_num_ctx == 2560
    assert settings.generator_model_default == "custom:3b"


def test_unknown_profile_fails_with_actionable_message() -> None:
    with pytest.raises(ValueError, match="Unsupported NIRMIQ_RUNTIME_PROFILE"):
        resolve_runtime_profile("unlimited")
