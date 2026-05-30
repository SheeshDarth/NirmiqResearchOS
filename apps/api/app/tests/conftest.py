import os
from pathlib import Path
from uuid import uuid4


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
TEST_RUNTIME_ROOT = WORKSPACE_ROOT / "temp" / "api-tests" / uuid4().hex

os.environ.setdefault("SQLITE_PATH", str(TEST_RUNTIME_ROOT / "sqlite" / "nirmiq-test.db"))
os.environ.setdefault("CHROMA_PATH", str(TEST_RUNTIME_ROOT / "chroma"))
os.environ.setdefault("UPLOAD_PATH", str(TEST_RUNTIME_ROOT / "raw" / "uploads"))
os.environ.setdefault("PARSE_CACHE_PATH", str(TEST_RUNTIME_ROOT / "cache" / "parsed_pages"))
os.environ.setdefault("USE_OLLAMA_GENERATION", "false")
os.environ.setdefault("USE_OLLAMA_EMBEDDINGS", "false")
os.environ.setdefault("USE_OLLAMA_RERANKER", "false")
