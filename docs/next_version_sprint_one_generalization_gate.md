# Next-Version Sprint One - RAG Generalization Gate

Status: Sprint 1A implemented and verified.

Last updated: 2026-07-24

## Goal

Make NIRMIQ's RAG reliability measurable on expanding, unseen academic material before adding more retrieval heuristics or model complexity.

The purpose is not to overfit the existing 40 examples. The purpose is to create a repeatable quality gate that can grow from the current corpus toward a broader student/researcher workload.

## Why This Sprint Comes First

The review sprint found that NIRMIQ is already strong as a local-first portfolio/demo MVP, but the biggest remaining risk is generalization:

- Current RAG metrics are strong.
- The eval corpus is still modest.
- Real users may upload unseen textbooks, lecture notes, papers, scans, diagrams, tables, equations, and noisy notes.
- The next version should prove reliability across more source types before claiming a broader product.

## Implemented In Sprint 1A

- Added `data/processed/eval/generalization_gate.json` as the gate manifest.
- Added `scripts/validate_eval_gate.py` to validate metrics and dataset coverage against the manifest.
- Added `scripts/eval_generalization_gate.ps1` to run the full BM25/offline answer-quality path and then validate the gate.
- Added `npm run eval:generalization-gate`.
- Added unit tests for the validator.

## Current Gate

Current dataset:

- `data/processed/eval/real_world_answer_quality.jsonl`
- `40` reviewed examples.
- `3` source files.
- `11` categories.
- `2` unanswerable examples.

Current mode:

- BM25.
- Ollama generation disabled by default.
- Ollama embeddings disabled.
- Reranker disabled.
- Vector retrieval disabled.
- Low-memory mode enabled.

Current thresholds:

- MRR: `>= 0.700`
- Recall@8: `>= 0.850`
- Expected citation coverage: `>= 0.900`
- Answer-quality pass rate: `>= 0.900`
- Overall answer score: `>= 0.850`
- Answer relevance: `>= 0.750`
- Concept coverage: `>= 0.750`
- Query focus: `>= 0.700`
- Readability: `>= 0.900`
- Faithfulness: `>= 0.950`
- Answerability correctness: `1.000`

Latest verification:

- Command: `npm.cmd run eval:generalization-gate`
- Status: `PASS`
- Runtime: `261.297 s`
- MRR: `0.934`
- Recall@8: `1.000`
- Expected citation coverage: `1.000`
- Answer-quality pass rate: `1.000`
- Overall answer score: `0.940`
- Faithfulness: `0.995`
- Answerability correctness: `1.000`
- Empty failures file: `data/processed/eval/generalization_gate_failures.jsonl`

## Command

```powershell
npm.cmd run eval:generalization-gate
```

Outputs:

- `data/processed/eval/generalization_gate_metrics.json`
- `data/processed/eval/generalization_gate_failures.jsonl`
- `data/processed/eval/generalization_gate_report.json`

## Next Slices

1. Expand the dataset to at least `100` reviewed natural queries.
2. Stretch to `150` queries if time allows.
3. Add at least `5` source files.
4. Add unseen textbooks, notes, papers, slides, scanned pages, diagrams, equations, tables, and handwritten/noisy samples.
5. Keep a blind holdout set that is not tuned after seeing failures.
6. Convert real-user `Needs work` feedback into eval candidates only after human evidence review.

## Acceptance Boundary

This sprint should not:

- Add cloud dependencies.
- Add a graph database.
- Add agentic orchestration.
- Tune only the current 40 examples.
- Hide failures by lowering thresholds.

This sprint should:

- Make failures easier to reproduce.
- Keep BM25/offline mode trustworthy.
- Make answer quality visible by category.
- Preserve simple UI behavior while improving backend evidence reliability.
