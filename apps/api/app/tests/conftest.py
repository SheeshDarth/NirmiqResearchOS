import os
from pathlib import Path
from uuid import uuid4


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
configured_runtime_root = os.environ.get("NIRMIQ_TEST_RUNTIME_ROOT")
TEST_RUNTIME_BASE = (
    Path(configured_runtime_root)
    if configured_runtime_root
    else WORKSPACE_ROOT / "temp" / "api-tests"
)
TEST_RUNTIME_ROOT = TEST_RUNTIME_BASE / uuid4().hex

# Tests must never inherit production data paths from the caller's environment.
os.environ["SQLITE_PATH"] = str(TEST_RUNTIME_ROOT / "sqlite" / "nirmiq-test.db")
os.environ["CHROMA_PATH"] = str(TEST_RUNTIME_ROOT / "chroma")
os.environ["UPLOAD_PATH"] = str(TEST_RUNTIME_ROOT / "raw" / "uploads")
os.environ["PARSE_CACHE_PATH"] = str(TEST_RUNTIME_ROOT / "cache" / "parsed_pages")
os.environ.setdefault("USE_OLLAMA_GENERATION", "false")
os.environ.setdefault("USE_OLLAMA_EMBEDDINGS", "false")
os.environ.setdefault("USE_OLLAMA_RERANKER", "false")
os.environ.setdefault("SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS", "true")
