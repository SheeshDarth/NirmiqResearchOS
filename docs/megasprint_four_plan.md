# MegaSprint Four Plan: Local Runtime Optimization

## Goal

Make NIRMIQ predictable on an RTX 4050, low-memory laptops, CPU-only Windows, and low-end Linux without weakening retrieval, citations, or offline operation.

## Scope

1. Establish repeatable startup, readiness, query-latency, RAM, and VRAM baselines.
2. Consolidate scattered environment settings into internal runtime profiles.
3. Prevent model churn and unbounded context or embedding batches.
4. Preserve BM25 and deterministic synthesis when optional local models are unavailable.
5. Verify Windows desktop and Linux startup paths.
6. Add release-budget warnings only after representative baselines are recorded.

## Runtime Profiles

- `auto`: selects `low_memory` below 12 GiB RAM and `balanced` otherwise.
- `balanced`: local generation, local embeddings, hybrid retrieval, 3072-token model context, and bounded batches.
- `low_memory`: local generation with short model residency, BM25-only retrieval, no embedding-model swap, and a smaller context budget.
- `cpu_offline`: no Ollama dependency; BM25 plus deterministic grounded synthesis remains available.

Explicit environment values override profile defaults. Profiles are backend policy and do not add normal-user UI controls.

## Initial Performance Budgets

These are guardrails to validate, not claims about measurements already achieved.

| Critical path | Balanced target | Low-resource target |
| --- | ---: | ---: |
| Warm `/health/readiness` p95 | <= 500 ms | <= 750 ms |
| Grounded BM25 fallback query p95 | <= 3 s | <= 5 s |
| Local generated query p50 | <= 25 s | <= 45 s |
| API cold readiness | <= 20 s | <= 30 s |
| Desktop cold readiness | <= 75 s | <= 90 s |
| RTX 4050 peak VRAM | <= 5.5 GiB | <= 4.5 GiB |
| API RSS excluding Ollama | <= 1.5 GiB | <= 1.0 GiB |

Accuracy guardrails remain mandatory:

- Recall@8 >= `0.850` as the real-world set grows.
- MRR >= `0.700`.
- Expected citation coverage >= `0.900`.
- Unsupported questions abstain instead of generating filler.

## Delivery Blocks

### Block 1: Profiles And Probe

Status: complete and verified on 2026-07-12.

- Add runtime-profile resolution with safe RAM detection.
- Add `npm run benchmark:runtime` for bounded local measurements.
- Report the active profile through readiness diagnostics.
- Preserve explicit environment overrides and public query contracts.

Verification:

- Focused profile/runtime tests: `10 passed`, `1 warning`.
- Full ship gate: `100 passed`, web production build passed, publish smoke passed, and golden demo passed.
- Windows desktop smoke: passed with local API, readiness, web shell, and cloud-free operation verified.

### Block 2: Representative Baseline

Status: complete on the representative Windows/RTX 4050 path; broader query-set and Linux measurements remain in Block 4.

- Record cold startup and warm readiness.
- Measure BM25 fallback and local Ollama generation separately.
- Record process RAM and `nvidia-smi` VRAM when available.
- Use a larger real-world query set; do not tune against the existing 17 cases.

First Windows/RTX 4050 observation:

- Balanced-profile warm readiness is fast, but the first measured grounded BM25 query took `56.5 s`.
- The requested `phi3:mini` model was not installed, so the legacy fallback order selected a 7B model before an available 4B model.
- A trial that preferred the installed Qwen 4B model took `64.0 s` and produced no usable answer text, so faithfulness handling fell back to deterministic synthesis. The selector change was rejected rather than shipping a benchmark-only regression.
- The next model test should use the intended Qwen 2.5 3B instruct or Phi-3 Mini runtime, then compare cold and warm runs before changing defaults.

Measured model comparison on 2026-07-13 using the same selected 2,842-chunk textbook, BM25 retrieval, and `What is a Gaussian mixture model?`:

| Local model | Artifact | Cold query | Warm query | Grounded | Citation coverage | Decision |
| --- | --- | ---: | ---: | --- | ---: | --- |
| Mistral 7B fallback | Q4_K_M, 4.4 GB | `56.47 s` | not recorded | yes | citations present | Reject as automatic small-device fallback |
| Qwen 2.5 3B | Q4_K_M, 1.9 GB | `8.90 s` | `5.18 s` | yes | `1.00` | Fast opt-in research profile; Qwen-license disclosure required |
| Phi-3 Mini | Q4_0, 2.2 GB | `29.32 s` | `10.69 s` | yes | `0.75` | Keep as MIT-licensed publishable default |

Implementation decision:

- Keep `phi3:mini` as the default because it is MIT licensed and explicitly intended for commercial and research use.
- Move small 3B/2B models ahead of Mistral 7B in automatic fallback order.
- Do not silently distribute or promote Qwen 2.5 3B without its model-license disclosure, even though it is materially faster on this machine.
- Benchmark output now separates first/cold and warm query samples and can record API RSS and NVIDIA GPU memory without extra Python dependencies.

Verification:

- Runtime-focused unit tests: `9 passed`.
- Full release gate: `101 passed`, production web build passed, publish smoke passed, golden demo passed, and unsupported-query abstention passed.
- Windows desktop package and smoke test passed after the UI and runtime updates.

### Block 3: Model Residency And Scheduling

- Ensure embedding and generation work cannot create uncontrolled model churn.
- Add bounded concurrency and cancellation around local generation.
- Validate Ollama keep-alive behavior for each profile.

### Block 4: Cross-Platform Hardening

- Verify CPU-only Windows and Linux startup.
- Validate path, OCR, SQLite, Chroma-optional, and shutdown behavior.
- Document hardware-specific recommendations without making them mandatory.

### Block 5: Release Enforcement

- Add stable budgets to the ship gate only after repeatable baselines exist.
- Fail on accuracy regressions; warn on noisy local-hardware latency variance.
- Publish benchmark results and remaining constraints.

## Out Of Scope

- Cloud inference as a requirement.
- Larger local models as the first optimization.
- Graph databases, multi-agent frameworks, or new normal-user controls.
- UI redesign. MegaSprint Two owns core UI simplification; MegaSprint Five owns final release visual QA.
