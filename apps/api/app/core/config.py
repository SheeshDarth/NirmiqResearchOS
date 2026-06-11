from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    api_host: str
    api_port: int
    web_allowed_origins: list[str]
    log_level: str
    workspace_root: Path
    sqlite_path: Path
    chroma_path: Path
    upload_path: Path
    parse_cache_path: Path
    local_ingest_allowed_roots: list[Path]
    security_allow_arbitrary_local_paths: bool
    ollama_base_url: str
    embed_model: str
    reranker_model: str
    generator_model_default: str
    generator_model_code: str
    use_ollama_generation: bool
    use_ollama_embeddings: bool
    use_ollama_reranker: bool
    ollama_timeout_seconds: float
    low_memory_mode: bool
    ollama_keep_alive: str
    ollama_num_ctx: int
    ollama_num_predict: int
    ollama_num_gpu: int | None
    ollama_num_thread: int | None
    ollama_embed_batch_size: int
    generator_temperature_grounded: float
    generator_temperature_long_context: float
    retrieval_k_bm25: int
    retrieval_k_vector: int
    retrieval_k_fused: int
    retrieval_k_rerank: int
    retrieval_rrf_k: int
    retrieval_max_chunks_per_document: int
    retrieval_enable_vector: bool
    retrieval_max_context_tokens: int
    retrieval_min_grounding_score: float
    memory_snapshot_interval_messages: int
    memory_snapshot_window_messages: int

    @classmethod
    def from_env(cls) -> "Settings":
        workspace_root = Path(__file__).resolve().parents[4]
        sqlite_default = workspace_root / "data" / "sqlite" / "nirmiq.db"
        chroma_default = workspace_root / "data" / "indexes" / "chroma"
        upload_default = workspace_root / "data" / "raw" / "uploads"
        parse_cache_default = workspace_root / "data" / "cache" / "parsed_pages"
        allowed_roots_default = f"{workspace_root / 'data' / 'raw'},{upload_default}"
        local_ingest_allowed_roots = [
            Path(part.strip())
            for part in os.getenv("LOCAL_INGEST_ALLOWED_ROOTS", allowed_roots_default).split(",")
            if part.strip()
        ]
        return cls(
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8000")),
            web_allowed_origins=[
                part.strip()
                for part in os.getenv(
                    "WEB_ALLOWED_ORIGINS",
                    "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:3002,http://localhost:3002",
                ).split(",")
                if part.strip()
            ],
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            workspace_root=workspace_root,
            sqlite_path=Path(os.getenv("SQLITE_PATH", str(sqlite_default))),
            chroma_path=Path(os.getenv("CHROMA_PATH", str(chroma_default))),
            upload_path=Path(os.getenv("UPLOAD_PATH", str(upload_default))),
            parse_cache_path=Path(os.getenv("PARSE_CACHE_PATH", str(parse_cache_default))),
            local_ingest_allowed_roots=local_ingest_allowed_roots,
            security_allow_arbitrary_local_paths=(
                os.getenv("SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS", "false").lower() == "true"
            ),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            embed_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            reranker_model=os.getenv("RERANKER_MODEL", "bge-reranker-base"),
            generator_model_default=os.getenv("GENERATOR_MODEL_DEFAULT", "phi3:mini"),
            generator_model_code=os.getenv("GENERATOR_MODEL_CODE", "deepseek-coder:6.7b"),
            use_ollama_generation=os.getenv("USE_OLLAMA_GENERATION", "true").lower() == "true",
            use_ollama_embeddings=os.getenv("USE_OLLAMA_EMBEDDINGS", "true").lower() == "true",
            use_ollama_reranker=os.getenv("USE_OLLAMA_RERANKER", "false").lower() == "true",
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120.0")),
            low_memory_mode=os.getenv("LOW_MEMORY_MODE", "true").lower() == "true",
            ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "45s"),
            ollama_num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "3072")),
            ollama_num_predict=int(os.getenv("OLLAMA_NUM_PREDICT", "512")),
            ollama_num_gpu=cls._optional_int(os.getenv("OLLAMA_NUM_GPU")),
            ollama_num_thread=cls._optional_int(os.getenv("OLLAMA_NUM_THREAD")),
            ollama_embed_batch_size=max(1, int(os.getenv("OLLAMA_EMBED_BATCH_SIZE", "8"))),
            generator_temperature_grounded=float(os.getenv("GENERATOR_TEMPERATURE_GROUNDED", "0.15")),
            generator_temperature_long_context=float(os.getenv("GENERATOR_TEMPERATURE_LONG_CONTEXT", "0.85")),
            retrieval_k_bm25=int(os.getenv("RETRIEVAL_K_BM25", "20")),
            retrieval_k_vector=int(os.getenv("RETRIEVAL_K_VECTOR", "20")),
            retrieval_k_fused=int(os.getenv("RETRIEVAL_K_FUSED", "24")),
            retrieval_k_rerank=int(os.getenv("RETRIEVAL_K_RERANK", "8")),
            retrieval_rrf_k=int(os.getenv("RETRIEVAL_RRF_K", "60")),
            retrieval_max_chunks_per_document=int(os.getenv("RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT", "2")),
            retrieval_enable_vector=os.getenv("RETRIEVAL_ENABLE_VECTOR", "true").lower() == "true",
            retrieval_max_context_tokens=int(os.getenv("RETRIEVAL_MAX_CONTEXT_TOKENS", "2400")),
            retrieval_min_grounding_score=float(os.getenv("RETRIEVAL_MIN_GROUNDING_SCORE", "0.15")),
            memory_snapshot_interval_messages=int(os.getenv("MEMORY_SNAPSHOT_INTERVAL_MESSAGES", "6")),
            memory_snapshot_window_messages=int(os.getenv("MEMORY_SNAPSHOT_WINDOW_MESSAGES", "12")),
        )

    @staticmethod
    def _optional_int(raw_value: str | None) -> int | None:
        if raw_value is None or not raw_value.strip():
            return None
        return int(raw_value)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
