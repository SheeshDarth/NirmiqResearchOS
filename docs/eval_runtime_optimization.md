# Evaluation Runtime Optimization

Status: Remaining Job 4 started on 2026-07-21.

## Purpose

The strict academic answer-quality gate is useful because it runs the real
`POST /query` path with Ollama, embeddings, vectors, and reranking disabled.
Its weakness is runtime: the 40-case BM25-only gate previously took about
`310.8s` on the local Windows corpus. Job 4 focuses on making that proof path
faster and more diagnosable without weakening retrieval, answer quality, or
offline behavior.

## Implemented Block

- Added a bounded in-process BM25 corpus cache.
- Cache identity includes BM25 parameters, ordered active chunk IDs, document
  IDs, chunk text hashes, and searchable metadata such as heading, section path,
  chunk type, and key terms.
- Added selected-document active row reuse inside `RetrievalService`.
- The selected-document row cache validates against document ID, content hash,
  status, updated timestamp, and active chunk count before reuse.
- Added debug-only retrieval diagnostics for BM25 corpus cache hits and selected
  document row cache hits.
- Added evaluator runtime metadata:
  - source resolution seconds
  - per-mode seconds
  - total seconds
  - runtime cache counters
  - per-mode sample latency summaries
- Added `--sample-limit` to `scripts/eval_retrieval.py` for quick local
  diagnostic runs.
- Added `npm run eval:answer-quality` as the canonical package script for the
  strict answer-quality gate.

## Measured Local Result

Strict BM25-only full-query run against
`data/processed/eval/real_world_answer_quality.jsonl`:

| Measure | Before | Job 4 Block 1 |
| --- | ---: | ---: |
| Samples | 40 | 40 |
| MRR | 0.934 | 0.934 |
| Recall@8 | 1.000 | 1.000 |
| Expected citation coverage | 1.000 | 1.000 |
| Answer-quality pass | 1.000 | 1.000 |
| Faithfulness | 0.995 | 0.995 |
| Runtime | `310.8s` | `274.3s` |

The measured reduction is roughly `11.7%` on this machine. The final telemetry run
reported selected-document row cache `37` hits / `3` misses and BM25 corpus cache
`37` hits / `3` misses / `0` evictions.

Quick three-sample diagnostic after evaluator telemetry was added:

- Total runtime: `9.0s`.
- Active document row cache: `2` hits, `1` miss.
- BM25 corpus cache: `2` hits, `1` miss.
- Quality pass: `3/3`.

## Tradeoffs

- This is an in-process cache. It speeds repeated queries in the same API or
  evaluator process; it does not persist tokenized BM25 state across restarts.
- Cache keys intentionally prefer correctness over perfect minimal hashing, so
  metadata changes can invalidate a corpus even when the raw text is unchanged.
- The evaluator now reports timing diagnostics, but the thresholds are still
  advisory because local hardware varies.
- The remaining runtime likely comes from answer orchestration and repeated
  candidate scoring, not only BM25 tokenization.

## Next Job 4 Blocks

1. Add optional strict-gate performance budgets as warnings, not hard failures.
2. Add an eval profile that records the slowest samples and retrieval stages.
3. Consider bounded reuse of section-ranking and direct-evidence scoring only if
   profiling shows it is still a hotspot.
4. Keep the full 40-case gate authoritative; use `--sample-limit` only for local
   debugging.
