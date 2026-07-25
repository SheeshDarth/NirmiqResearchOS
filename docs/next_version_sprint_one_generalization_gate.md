# Next-Version Sprint One - RAG Generalization Gate

Status: complete
Last updated: 2026-07-25

## Purpose

Sprint One exists to keep NIRMIQ honest while improving RAG quality. The goal is not to pass a few hand-picked prompts. The goal is to maintain a query-agnostic, local-first reliability gate that covers the kinds of questions students and researchers naturally ask over uploaded academic material.

The active gate checks the full answer path, not only raw retrieval. It verifies retrieval rank, citation expected coverage, answer relevance, concept coverage, query focus, readability, faithfulness, and abstention correctness.

## Design Rules

- Keep the gate local-first and offline-first.
- Use BM25 as the required safe backbone.
- Disable Ollama generation, Ollama embeddings, vector search, and reranking by default.
- Do not add cloud dependencies, graph databases, agent frameworks, or larger model requirements.
- Do not change the public `POST /query` request shape.
- Do not hide failures by lowering thresholds.

## Implemented In Sprint 1A

- Added `data/processed/eval/generalization_gate.json` as the gate manifest.
- Added `scripts/validate_eval_gate.py`.
- Added `scripts/eval_generalization_gate.ps1`.
- Added `npm run eval:generalization-gate`.
- Added `apps/api/app/tests/unit/test_generalization_gate_validator.py`.
- Added this sprint document.

## Implemented In Sprint 1B

- Added `scripts/audit_eval_dataset.py`.
- Added `scripts/eval_dataset_audit.ps1`.
- Added `npm run eval:dataset-audit`.
- Added `data/processed/eval/generalization_dataset_audit.json`.
- Added [`generalization_dataset_audit.md`](generalization_dataset_audit.md).
- Added unit tests for dataset coverage and label-quality warnings.

## Implemented In Sprint 1C

- Expanded `data/processed/eval/real_world_answer_quality.jsonl` from `40` to `110` reviewed examples.
- Raised gate dataset requirements to at least `100` samples, `5` source files, `10` unanswerable prompts, and all `18` target query categories.
- Added committed local source fixtures for prompt engineering, website-building notes, generative-AI module notes, scans, handwriting, equations, tables, diagrams, and hard-document transcripts.
- Added hash-aware auto-reindexing for eval source files so changed source text cannot reuse stale indexed rows.
- Hardened eval artifact publishing with isolated temp runtime directories and byte-stable writes.
- Improved deterministic intent, answer planning, and fallback synthesis for exam, paper, factual, procedure, limitation, equation, local-first privacy, text-generation mechanism, and question-bank prompts.
- Improved answer-quality scoring so correct abstentions and structural headings are not punished as weak answers.

## Active Gate

Dataset:

- `data/processed/eval/real_world_answer_quality.jsonl`
- `110` reviewed examples.
- `14` source files.
- `18` categories.
- `10` unanswerable examples.

Categories:

- architecture
- comparison
- definition
- diagram
- enumeration
- equation
- exam
- explanation
- factual_lookup
- handwriting
- limitations
- mechanism
- paper_draft
- procedure
- scanned_pdf
- summary
- table
- unanswerable

Mode:

- BM25.
- Ollama generation disabled by default.
- Ollama embeddings disabled.
- Reranker disabled.
- Vector retrieval disabled.
- Low-memory mode enabled.

Thresholds:

- Minimum samples: `100`.
- Minimum source files: `5`.
- Minimum unanswerable examples: `10`.
- MRR: `>= 0.700`.
- Recall@8: `>= 0.850`.
- Expected citation coverage: `>= 0.900`.
- Answer-quality pass rate: `>= 0.900`.
- Overall answer score: `>= 0.850`.
- Answer relevance: `>= 0.750`.
- Concept coverage: `>= 0.750`.
- Query focus: `>= 0.700`.
- Readability: `>= 0.900`.
- Faithfulness: `>= 0.950`.
- Answerability correctness: `1.000`.

## Latest Verification

Command:

```powershell
npm.cmd run eval:generalization-gate
```

Result:

- Status: `PASS`.
- Runtime: `457.262 s`.
- MRR: `0.903`.
- Recall@3: `0.930`.
- Recall@5: `0.930`.
- Recall@8: `0.930`.
- Expected citation coverage: `0.930`.
- Answer-quality pass rate: `0.927`.
- Overall answer score: `0.941`.
- Answer relevance: `0.841`.
- Concept coverage: `0.864`.
- Query focus: `0.788`.
- Readability: `0.990`.
- Faithfulness: `0.998`.
- Answerability correctness: `1.000`.
- Remaining failure records: `8`, all `low_answer_relevance`.

Weakest categories:

- `explanation`: `5/9` pass rate.
- `factual_lookup`: `3/5` pass rate.
- `limitations`: `6/7` pass rate.
- `mechanism`: `11/12` pass rate.

## Commands

Run the active gate:

```powershell
npm.cmd run eval:generalization-gate
```

Outputs:

- `data/processed/eval/generalization_gate_metrics.json`
- `data/processed/eval/generalization_gate_failures.jsonl`
- `data/processed/eval/generalization_gate_report.json`

Run the dataset audit:

```powershell
npm.cmd run eval:dataset-audit
```

Outputs:

- `data/processed/eval/generalization_dataset_audit.json`
- `docs/generalization_dataset_audit.md`

## Closure Criteria

Sprint One is complete because:

- The gate now exceeds `100` reviewed examples.
- The gate covers all target query categories.
- The gate includes at least `10` unanswerable prompts.
- The gate uses at least `5` source files.
- The active offline BM25 path passes all required thresholds.
- Backend tests, compile, web build, dataset audit, and published gate validation are green.

## Remaining Accuracy Work

Do not overfit the `8` known failures directly. The next reliability sprint should add unseen sources and fresh natural prompts in the same weak categories, then improve retrieval and answer planning only when the new failures repeat.

Recommended next focus:

1. Explanation quality over longer textbook sections.
2. Factual lookup precision for names, dates, definitions, lists, and small facts.
3. Mechanism answers that explain process flow instead of listing related terms.
4. Limitation answers that separate true limitations from adjacent context.
5. Faster eval runtime through safe corpus reuse without weakening isolation.

## Follow-Up Precision Slice: 2026-07-25

The first reliability slice after Sprint One is complete. It added generic subject
extraction, mechanism operation focus, factual query expansion, and a citation-preserving
fallback for ordinary factual measurements. The implementation is documented in
[`next_version_sprint_two_explanation_factual_precision.md`](next_version_sprint_two_explanation_factual_precision.md).

The full 110-case gate remains green with the following latest metrics:

- MRR: `0.903`.
- Recall@8: `0.940`.
- Expected citation coverage: `0.940`.
- Answer-quality pass rate: `0.955`.
- Answer relevance: `0.854`.
- Concept coverage: `0.876`.
- Query focus: `0.802`.
- Faithfulness: `0.998`.
- Answerability correctness: `1.000`.

The current residuals are visible rather than suppressed: explanation quality and
phrase-level retrieval still need section-aware candidate selection for long textbook
passages. The next work should use unseen sources and fresh queries to avoid overfitting.

## Acceptance Boundary

This sprint did not:

- Add cloud dependencies.
- Add a graph database.
- Add agentic orchestration.
- Add a larger required model.
- Change public API contracts.
- Claim universal arbitrary-document accuracy.

This sprint did:

- Make failures easier to reproduce.
- Keep BM25/offline mode trustworthy.
- Make answer quality visible by category.
- Preserve simple UI behavior while improving backend evidence reliability.
