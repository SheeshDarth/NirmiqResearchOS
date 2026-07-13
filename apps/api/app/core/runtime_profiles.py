from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    generator_model_default: str
    low_memory_mode: bool
    use_ollama_generation: bool
    use_ollama_embeddings: bool
    use_ollama_reranker: bool
    ollama_keep_alive: str
    ollama_num_ctx: int
    ollama_num_predict: int
    ollama_embed_batch_size: int
    retrieval_enable_vector: bool
    retrieval_max_context_tokens: int


RUNTIME_PROFILES: dict[str, RuntimeProfile] = {
    "balanced": RuntimeProfile(
        name="balanced",
        generator_model_default="qwen3.5:4b",
        low_memory_mode=False,
        use_ollama_generation=True,
        use_ollama_embeddings=True,
        use_ollama_reranker=False,
        ollama_keep_alive="45s",
        ollama_num_ctx=3072,
        ollama_num_predict=512,
        ollama_embed_batch_size=8,
        retrieval_enable_vector=True,
        retrieval_max_context_tokens=2400,
    ),
    "low_memory": RuntimeProfile(
        name="low_memory",
        generator_model_default="phi3:mini",
        low_memory_mode=True,
        use_ollama_generation=True,
        use_ollama_embeddings=False,
        use_ollama_reranker=False,
        ollama_keep_alive="15s",
        ollama_num_ctx=2048,
        ollama_num_predict=384,
        ollama_embed_batch_size=4,
        retrieval_enable_vector=False,
        retrieval_max_context_tokens=1800,
    ),
    "cpu_offline": RuntimeProfile(
        name="cpu_offline",
        generator_model_default="phi3:mini",
        low_memory_mode=True,
        use_ollama_generation=False,
        use_ollama_embeddings=False,
        use_ollama_reranker=False,
        ollama_keep_alive="0s",
        ollama_num_ctx=1536,
        ollama_num_predict=256,
        ollama_embed_batch_size=2,
        retrieval_enable_vector=False,
        retrieval_max_context_tokens=1600,
    ),
}


def resolve_runtime_profile(
    requested: str,
    *,
    total_memory_bytes: int | None = None,
) -> RuntimeProfile:
    normalized = requested.strip().lower().replace("-", "_")
    if normalized == "auto":
        detected_memory = total_memory_bytes
        if detected_memory is None:
            detected_memory = detect_total_memory_bytes()
        normalized = "low_memory" if detected_memory and detected_memory < 12 * 1024**3 else "balanced"
    try:
        return RUNTIME_PROFILES[normalized]
    except KeyError as exc:
        choices = ", ".join(["auto", *RUNTIME_PROFILES])
        raise ValueError(f"Unsupported NIRMIQ_RUNTIME_PROFILE '{requested}'. Choose: {choices}.") from exc


def detect_total_memory_bytes() -> int | None:
    """Return physical memory without launching slow platform inventory commands."""
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
                return int(status.total_physical)
        except (AttributeError, OSError):
            return None
        return None

    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        page_count = int(os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return page_size * page_count if page_size > 0 and page_count > 0 else None
