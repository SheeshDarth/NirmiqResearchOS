#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/temp/linux-ci-smoke"
SOURCE_DIR="$RUNTIME_DIR/source"
API_PORT="${API_PORT:-8015}"
API_BASE="http://127.0.0.1:$API_PORT"

mkdir -p "$SOURCE_DIR"

export PYTHONPATH="${PYTHONPATH:-$ROOT/apps/api}"
export NIRMIQ_RUNTIME_PROFILE="${NIRMIQ_RUNTIME_PROFILE:-cpu_offline}"
export USE_OLLAMA_GENERATION="false"
export USE_OLLAMA_EMBEDDINGS="false"
export USE_OLLAMA_RERANKER="false"
export RETRIEVAL_ENABLE_VECTOR="false"
export LOW_MEMORY_MODE="true"
export SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS="true"
export SQLITE_PATH="$RUNTIME_DIR/sqlite/nirmiq-linux-smoke.db"
export CHROMA_PATH="$RUNTIME_DIR/chroma"
export UPLOAD_PATH="$RUNTIME_DIR/uploads"
export PARSE_CACHE_PATH="$RUNTIME_DIR/parse-cache"
export DIAGRAM_PATH="$RUNTIME_DIR/diagrams"

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

cat >"$SOURCE_DIR/linux_offline_smoke.md" <<'EOF'
# NIRMIQ Linux Offline Smoke

## Local Runtime

NIRMIQ runs locally on Linux through a FastAPI backend and a browser-based Next.js
frontend. Its low-end profile keeps Ollama, embeddings, vector search, and reranking
optional so the BM25 retrieval path remains usable without GPU VRAM.

The Linux browser mode is meant for machines where a native desktop package is not yet
validated. The API binds to 127.0.0.1, the web app runs in the user's browser, and the
project can still answer from local files when optional model services are absent.

## Offline Retrieval

BM25 is the reliable offline backbone for low-end Linux. It scores local document chunks
lexically, keeps citations connected to source passages, and can run without Chroma,
Ollama, embedding models, rerankers, cloud APIs, or a dedicated GPU.

When the user asks a grounded question, NIRMIQ retrieves evidence from uploaded study
material, builds a source-only answer, and shows citations. If the document does not
contain enough evidence, the system should abstain instead of guessing.

## Privacy Boundary

For privacy, uploaded academic material stays on the user's machine by default. Grounded
answers should cite the local source material and should avoid guessing when evidence is
missing.

Local-first behavior means the app does not require internet access to index plain text
notes, retrieve BM25 evidence, or produce deterministic citation-backed fallback answers.
External APIs remain optional add-ons rather than the core operating path.

## Low-End Operating Rules

On a low-end Linux laptop, NIRMIQ should prefer the cpu_offline runtime profile. That
profile disables local generation by default, keeps embeddings and reranking off, and
uses deterministic cited synthesis when the retrieved evidence is strong enough. This is
less conversational than a loaded local LLM, but it is predictable, private, and usable
on machines with limited memory.

For larger textbooks, the first parse can still take CPU time, especially when the file is
scanned or image-heavy. Once text is extracted and indexed, common study questions should
use BM25 retrieval before any optional semantic path. The important product promise is
that the user can still ask questions, get source-backed answers, and inspect citations
without needing GPU VRAM or an internet connection.
EOF

(
  cd "$ROOT/apps/api"
  python -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT"
) >"$RUNTIME_DIR/api.out.log" 2>"$RUNTIME_DIR/api.err.log" &
API_PID="$!"

python - "$API_BASE" <<'PY'
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

base = sys.argv[1]
deadline = time.time() + 30
last_error = None
while time.time() < deadline:
    try:
        with urlopen(f"{base}/health", timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except URLError as exc:
        last_error = exc
    time.sleep(1)
raise SystemExit(f"API did not become ready: {last_error}")
PY

python - "$API_BASE" "$SOURCE_DIR/linux_offline_smoke.md" <<'PY'
import json
import sys
from urllib.request import Request, urlopen

base = sys.argv[1]
source = sys.argv[2]

def post_json(path: str, payload: dict) -> dict:
    request = Request(
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

ingest = post_json(
    "/ingest",
    {
        "source_path": source,
        "title": "Linux Offline Smoke",
        "mime_type": "text/markdown",
        "force_reindex": True,
    },
)
document_id = ingest["document_id"]
query = post_json(
    "/query",
    {
        "session_id": "linux-ci-smoke",
        "document_id": document_id,
        "query": "How does NIRMIQ run on low-end Linux without GPU VRAM?",
        "mode": "research",
        "retrieval_mode": "bm25",
        "retrieval_profile": "fast",
        "debug": True,
    },
)
answer = query.get("answer", "")
citations = query.get("citations", [])
meta = query.get("retrieval_meta") or {}
if not query.get("grounded"):
    raise SystemExit(f"Expected grounded response, got: {answer}")
if not citations:
    raise SystemExit(f"Expected at least one citation, got: {query}")
if "bm25" not in str(meta.get("effective_retrieval_mode", "")).lower():
    raise SystemExit(f"Expected BM25 effective path, got: {meta}")
if "gpu" not in answer.lower() and "bm25" not in answer.lower():
    raise SystemExit(f"Answer did not mention the low-end/BM25 evidence: {answer}")
print("LINUX_CI_SMOKE_PASS")
PY
