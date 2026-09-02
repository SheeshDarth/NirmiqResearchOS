# Evaluation Runtime Optimization

Status: Block 2 implemented on 2026-08-26; targeted optimization remains open.

## Purpose

The strict academic answer-quality gate is useful because it runs the real
`POST /query` path with Ollama, embeddings, vectors, and reranking disabled.
Its weakness is runtime: the 40-case BM25-only gate previously took about
`310.8s` on the local Windows corpus. Job 4 focuses on making that proof path
faster and more diagnosable without weakening retrieval, answer quality, or
offline behavior.

## Implemented Block 1

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

## Implemented Block 2

- Added debug-only query timing for memory lookup, planning, retrieval, selected-summary
  augmentation, synthesis, response assembly, and total orchestration.
- The evaluator now aggregates stage timing by mode with average, p50, p95, maximum,
  and share of total query time.
- Slowest-sample profiles include category, total latency, and the stage breakdown;
  `--slowest-samples` controls how many are retained.
- Added optional `--warn-total-seconds`, `--warn-source-resolution-seconds`, and
  `--warn-p95-sample-seconds` budgets. Exceeding them writes a structured warning
  and stderr notice but does not change the reliability gate exit code.
- The strict generalization manifest now carries advisory budgets of `660s` total,
  `180s` source resolution, and `25s` p95 sample latency. These are regression
  signals for the current Windows host, not portable release requirements.
- The answer-quality PowerShell wrapper exposes the same controls for local profiling.

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

1. Run the full 110-case strict gate with the new profile and rank retrieval,
   synthesis, and orchestration hotspots by measured share and p95 latency.
2. Consider bounded reuse of section ranking or direct-evidence scoring only if the
   profile shows one remains a repeated hotspot.
3. Keep the full 110-case gate authoritative; use `--sample-limit` only for local
   debugging.
4. Keep hardware budgets advisory until Windows, Linux, and low-end profiles have
   separate measured baselines.
