# Linux And Low-End Device Feasibility

Last updated: 2026-06-20

## Short Answer

NIRMIQ is feasible on Linux and low-end devices when it runs in browser-preview mode with the low-memory local profile.

Recommended low-end mode:

- API: FastAPI on `127.0.0.1:8000`.
- Web: Next.js on `127.0.0.1:3002`.
- Retrieval: BM25 first, vector/embeddings optional.
- Generation: deterministic extractive fallback by default, Ollama optional.
- Desktop: skip Electron on very low-end Linux devices unless later packaged specifically for Linux.

## Linux Quick Start

From the repo root:

```bash
python -m pip install -e apps/api
npm --prefix apps/web install
bash scripts/start_local.sh
```

Open:

```text
http://127.0.0.1:3002
```

Stop:

```bash
bash scripts/stop_local.sh
```

## Low-End Runtime Profile

The Linux launcher defaults to:

```bash
USE_OLLAMA_GENERATION=false
USE_OLLAMA_EMBEDDINGS=false
USE_OLLAMA_RERANKER=false
LOW_MEMORY_MODE=true
```

This keeps the app useful without GPU VRAM:

- PDFs can still be parsed and chunked locally.
- BM25 retrieval works without embeddings.
- Answers fall back to extractive, citation-grounded synthesis when no local LLM is available.
- Chroma/vector search remains optional.

## If Ollama Is Available

Use a small quantized model and bounded context:

```bash
export USE_OLLAMA_GENERATION=true
export USE_OLLAMA_EMBEDDINGS=false
export OLLAMA_NUM_CTX=2048
export OLLAMA_NUM_PREDICT=512
export OLLAMA_KEEP_ALIVE=20s
```

Recommended low-end behavior:

- Keep embeddings off unless retrieval quality requires them.
- Prefer BM25 or hybrid with deterministic embeddings.
- Avoid reranker models on CPU-only devices.
- Do not load multiple models at once.

## Minimum Practical Hardware

Likely usable:

- 4-core CPU.
- 8 GB RAM.
- SSD preferred.
- No GPU required for BM25 and extractive fallback.

Comfortable:

- 6+ CPU threads.
- 16 GB RAM.
- Small local Ollama model if desired.

RTX 4050 target:

- Use the documented low-memory Ollama profile.
- Keep context around `3072`.
- Keep prediction around `512-768`.
- Use short keep-alive to release VRAM sooner.

## Tradeoffs

- Low-end mode is more extractive and less conversational.
- Semantic retrieval may be weaker without embeddings.
- First PDF parse can still be CPU-heavy for large textbooks.
- Scanned PDFs need OCR tooling and will be slower.
- Electron desktop packaging is currently Windows-first; Linux should use browser-preview mode until a dedicated packaging sprint.

## Validation Status

Validated in the current Windows workspace:

- The backend and web runtime are already cross-platform Python/Node code.
- Docker Compose local config binds ports to `127.0.0.1`.

Not yet validated:

- Bash runtime/syntax check in this workspace, because WSL is installed without a Linux distribution.
- Native Linux desktop packaging.
- Low-end ARM devices.
- Very small RAM devices below 8 GB.
