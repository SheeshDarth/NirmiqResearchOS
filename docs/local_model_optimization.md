# NIRMIQ Local Model Optimization

Last updated: 2026-07-13

## Goal

Run NIRMIQ ResearchOS locally with low memory pressure while preserving grounded answer quality.

The project should prefer retrieval quality, citation verification, and context packing over larger models. A smaller quantized model with strong retrieval is usually better for this product than a large model that causes VRAM pressure, latency spikes, or crashes.

## Current Runtime Strategy

- Core operation is offline-first and local.
- Ollama is optional for generation and embeddings.
- Deterministic fallback synthesis keeps the app usable when Ollama is unavailable.
- Reranker model usage is disabled by default because a local LLM-based reranker can add latency and VRAM pressure.
- Retrieval remains hybrid-capable through BM25, optional vectors, RRF, and lexical fallback reranking.

## Low-Memory Defaults

The backend now uses bounded Ollama runtime defaults:

```text
NIRMIQ_RUNTIME_PROFILE=auto
OLLAMA_KEEP_ALIVE=45s
OLLAMA_NUM_CTX=3072
OLLAMA_NUM_PREDICT=512
OLLAMA_EMBED_BATCH_SIZE=8
USE_OLLAMA_RERANKER=false
```

Why this helps:

- Short keep-alive unloads local models sooner after use.
- Bounded context avoids accidentally loading an oversized KV cache.
- Bounded prediction caps long generations before they become runaway memory/latency events.
- Batched embeddings avoid sending every chunk to Ollama in one large request.
- Reranking stays lexical by default, so generation and reranking do not compete for VRAM.

## No-GPU / Low-End Linux Mode

NIRMIQ should remain useful without a GPU by leaning on retrieval and extractive fallback:

```bash
export USE_OLLAMA_GENERATION=false
export USE_OLLAMA_EMBEDDINGS=false
export USE_OLLAMA_RERANKER=false
export LOW_MEMORY_MODE=true
bash scripts/start_local.sh
```

This mode is best for:

- low-end Linux laptops
- CPU-only devices
- quick demos where reliability matters more than fluent generation
- reviewing retrieval/citation behavior without model variability

Tradeoff: answers become more extractive and less conversational, but they stay local and cited.

## Recommended Local Models

For RTX 4050-class hardware, prefer small quantized Ollama models:

- Balanced default: `qwen3.5:4b` (Apache 2.0 license)
- Low-memory default: `phi3:mini` (MIT license)
- Explicit-only research model: `qwen2.5:3b` (the installed Qwen Research License is non-commercial)
- Coding-heavy academic queries: `deepseek-coder:6.7b` only when needed
- Embeddings: `nomic-embed-text`

Representative Windows/RTX 4050 measurements on the same grounded textbook query:

- `phi3:mini`: `29.32 s` cold, `10.69 s` warm.
- `qwen2.5:3b`: `8.90 s` cold, `5.18 s` warm.
- Accidental Mistral 7B fallback: `56.47 s` cold.

These older three measurements used the same Gaussian-mixture query. The Qwen 3.5 figures below are live end-to-end acceptance timings on different prompts and should not be treated as a direct speed comparison.

Install the balanced default once:

```powershell
ollama pull qwen3.5:4b
```

Ollama generation sends `think=false`. This is required for thinking-capable models under NIRMIQ's bounded prediction budget; otherwise a model can spend the budget on hidden reasoning and return an empty visible response.

Use the low-memory profile with Phi-3 when RAM, VRAM, or latency stability requires it:

```powershell
ollama pull phi3:mini
$env:NIRMIQ_RUNTIME_PROFILE="low_memory"
```

Live answer-intelligence acceptance checks on 2026-07-13 used `qwen3.5:4b` against the selected 2,842-chunk textbook. They are not controlled model benchmarks, but they validate the end-to-end path:

- CNN explanation: approximately `24.8 s` cold; coherent cited answer after unsupported-claim pruning.
- Gaussian mixture model: approximately `19.9 s`; query-specific definition and mechanism.
- Random-forest comparison: approximately `20.3 s`; coherent comparison after orphan-fragment repair.

NIRMIQ still works through deterministic cited synthesis when Ollama or the selected model is unavailable.

Ollama-distributed small models are generally provided as quantized local artifacts. If importing your own GGUF, prefer Q4-class variants such as `Q4_K_M` before trying larger Q5/Q6 variants.

## Optional GPU/CPU Controls

Leave these unset for Ollama auto-placement unless the machine is unstable:

```powershell
$env:OLLAMA_NUM_GPU=""
$env:OLLAMA_NUM_THREAD=""
```

If VRAM spikes or the GPU becomes unstable, reduce GPU layer usage:

```powershell
$env:OLLAMA_NUM_GPU="20"
```

If CPU usage is too aggressive, cap threads:

```powershell
$env:OLLAMA_NUM_THREAD="6"
```

## Quality Guardrails

Lower memory must not mean weaker trust.

NIRMIQ preserves answer quality through:

- Document-scoped retrieval when a source is selected.
- Summary cache keyed by document id, content hash, and profile.
- Citation coverage scoring.
- Cited-claim verification.
- Extractive fallback rewrites for unsupported claims.
- Abstention when evidence is weak.

## Recommended Next Benchmarks

Run these after ingesting a real academic PDF:

```powershell
cd C:\Nirmiq-researchOS
$env:PYTHONPATH='apps/api'
python scripts/eval_retrieval.py --dataset data/processed/eval/qa_labels.jsonl --k 3 5 8 --modes hybrid bm25
```

Run the current real-world seed benchmark:

```powershell
.\scripts\eval_real_world.ps1
```

Track:

- summary latency first run versus cache hit
- memory stability during PDF ingest
- retrieval Recall@K
- citation coverage
- abstention correctness
- Ollama backend availability
