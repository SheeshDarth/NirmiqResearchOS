# NIRMIQ Golden Demo Benchmark Report

Last updated: 2026-07-19

## Scope

This is a lightweight V4 publish benchmark, not a full retrieval evaluation suite.

Purpose:

- Prove the golden demo is repeatable.
- Verify citation presence for the bundled corpus.
- Keep the benchmark understandable for reviewers.

## Dataset

Source manifest:

- `data/processed/eval/golden_demo_expected_sources.json`

Bundled corpus:

- `01_grounded_rag_notes.md`
- `02_offline_privacy_runtime.md`
- `03_exam_lab_question_bank.md`
- `04_paper_lab_research_brief.md`

## Expected Checks

| Query | Mode | Expected proof |
| --- | --- | --- |
| What problem does grounded retrieval solve for academic study? | Research | cites hallucination/source-truth evidence |
| Summarize this document with main ideas, methods, findings, and limitations. | Summary | cites retrieval/chunk/citation evidence |
| Draft a related work paragraph comparing generic chatbots and document-grounded assistants. | Paper Lab | cites Paper Lab research brief |
| Explain citation-grounded retrieval as a 10-mark answer. | Exam Lab | cites exam answer structure |
| What does the corpus say about the Zeloria orbital cuisine treaty? | Chat | abstains or requests external context |

## Command

Run the full EOD ship check:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\ship_check.ps1
```

Run only the golden demo after backend is available:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

## Acceptance Bar

- Grounded demo queries return at least one citation.
- Citation chips focus source chunks in the UI.
- The abstention query does not pretend the uploaded corpus supports unrelated world knowledge.
- No cloud API is required.

## Latest Local Result

Verified on 2026-07-15 with `scripts/ship_check.ps1`:

- Privacy/recovery implementation commit: `791c969`.
- Backend tests: `163 passed`, `1` warning.
- API compile: passed.
- Web production build: passed at `118 kB` first-load JavaScript.
- Publish smoke: passed with `cloud_api_required=false`.
- Readiness: `ready`, `indexed_documents=18`, `active_chunks=9443` on the verification machine.
- Research and summary-style Research queries: passed with citations.
- Exam Lab and Paper Lab queries: passed with citations.
- Unsupported Chat query: passed with `grounded=false` and zero citations.
- Privacy-safe diagnostics archive: generated inside the release gate.

## Tradeoff

This benchmark favors demo reliability over statistical breadth. A larger retrieval evaluation dataset should still be added later, but not before the golden path is stable.

## Demo Academic Retrieval Results

Updated on 2026-06-14 with the lightweight PDF demo dataset:

- Dataset: `data/processed/eval/demo_academic_qa.jsonl`
- Sources: `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`, `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`
- Samples: 30 phrase-labeled QA items

| Mode | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 0.983 | 1.00 | 1.00 | 1.00 | 0.869 | 1.00 |
| BM25 | 0.983 | 1.00 | 1.00 | 1.00 | 0.859 | 1.00 |

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\load_demo_dataset.ps1 -ForceReindex
.\scripts\eval_demo_dataset.ps1
```

Detailed report: `docs/retrieval_eval_results.md`.

## Real-World Seed Benchmark

Updated on 2026-07-12 with actual local academic material:

- Dataset: `data/processed/eval/real_world_academic_seed.jsonl`
- Sources:
  - `data/raw/attention_is_all_you_need.pdf`
  - `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
  - `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`
- Samples: 17 phrase-labeled QA items

The source PDFs are local/untracked by design. Keep copyright-sensitive textbooks and personal notes out of Git; commit labels and metrics only.

| Mode | MRR | Recall@3 | Recall@5 | Recall@8 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.843 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid | 0.804 | 1.000 | 1.000 | 1.000 | 1.000 |

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\eval_real_world.ps1
```

Interpretation:

- The golden demo remains the reviewer proof path.
- The real-world seed is the accuracy-improvement benchmark.
- The first reliability slice materially improved the real-world seed, but the set must grow before making broad launch-marketing claims.
- BM25 remains the safest offline backbone, while hybrid now performs better after direct-answer relevance was weighted more heavily during candidate ordering.
- Two real-world labels were corrected because source-valid evidence was being missed by OCR/wording-damaged expected phrases.
- The 2026-07-12 refresh produced no active weak retrieval records in `data/processed/eval/real_world_retrieval_failures.jsonl`.

## 2026-07-15 Ship Gate Refresh

Command:

```powershell
npm.cmd run ship:check
```

Result:

- Backend unit/integration tests: `163 passed`, `1 warning`.
- API compile: passed.
- Web production build: passed at `118 kB` first-load JavaScript.
- Publish smoke: passed.
- Golden demo: all four grounded demo queries returned citations.
- Abstention check: unsupported general-chat prompt returned `grounded=false` and `citations=0`.
- Diagnostics privacy smoke: passed without bundling raw logs or user content.

Release-hardening note:

- Golden Demo 02 privacy/runtime query required a targeted directness fix for local-first privacy controls before the ship gate passed.
- The fix did not reduce global evidence thresholds.

## 2026-07-19 MegaSprint Six Reliability Refresh

This is the current hardest answer-quality proof path, separate from the small golden demo.

Configuration:

- Full `POST /query` orchestration.
- BM25 only.
- Ollama generation, embeddings, and reranking disabled.
- Vector retrieval disabled.
- Low-memory mode enabled.
- Evaluation against answer-used full citation chunks.

| Samples | MRR | Recall@3 | Recall@8 | Expected citation coverage | Quality pass | Readability | Faithfulness | Answerability |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 40 | 0.921 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 0.995 | 1.000 |

Verification performed with the final code:

- Backend unit tests: `202 passed`.
- Backend integration tests: `10 passed`.
- Python compile: passed.
- Next.js production build: passed at `118 kB` first-load JavaScript.
- Failure records: none on this dataset.
- Full ship gate: passed with `212` backend tests, local publish smoke, four grounded golden-demo routes, correct unsupported-query abstention, and privacy-safe diagnostics export.

Release interpretation:

- NIRMIQ now has strong reproducible evidence for its strict offline textbook path.
- The result does not establish arbitrary-document accuracy or replace real-user QA.
- Next benchmark expansion should prioritize scans, tables, equations, diagrams, handwriting, additional textbooks, and natural questions not used during implementation.

## 2026-07-19 Hard-Document Offline Gate

This gate exercises the parser and query pipeline on generated files that are structurally different from the existing text-first corpus:

- A four-page textbook-like PDF containing a definition, formula, table, and embedded diagram.
- A two-page raster-only scanned PDF.
- A handwriting-style image note.
- One deliberately unsupported query.

Command:

```powershell
npm.cmd run eval:hard-docs
```

| Samples | MRR | Recall@3 | Recall@8 | Expected citation coverage | Quality pass | Faithfulness | Answerability |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.978 | 1.000 |

All OCR phrase, indexing, embedded-diagram extraction, retrieval, citation, answer-quality, and abstention gates passed. The evaluator uses BM25 with Ollama, vectors, embeddings, and reranking disabled, so it proves the low-memory offline path rather than GPU-assisted quality.

Post-change regression against the existing 40-case academic set also passed `40/40`: MRR `0.934`, Recall@8 `1.000`, expected citation coverage `1.000`, quality pass `1.000`, faithfulness `0.995`, and answerability `1.000`. The run took `310.8s`, confirming immutable-corpus/BM25 setup reuse as a performance priority for Remaining Job 4.

This is a deterministic engineering fixture, not a statistical or arbitrary-document benchmark. Its purpose is to prevent regressions in difficult file handling and generic equation/table reasoning. Independent real-user scans and textbooks remain necessary. Full methodology: [`hard_document_eval.md`](hard_document_eval.md).

## 2026-07-20 Recursive Summary Gate

A selected 2,842-chunk local textbook was summarized through the final all-chunk recursive path:

- `2,608` readable chunks inspected.
- `723` section groups and `22` chapter/appendix groups.
- `619` late non-content/index chunks excluded from displayed facts.
- Citation coverage `1.000`.
- First response `3.783 s`; cached response `0.191 s`.
- Chapter 19 and Appendix D retained; a parser-missed Chapter 17 heading was disclosed.

The final strict 40-case regression remained green: MRR `0.934`, Recall@8 `1.000`, expected citation coverage `1.000`, readability `0.985`, faithfulness `0.995`, and answerability `1.000`.

## 2026-07-21 Job 4 Runtime Optimization Start

The strict BM25-only full-query answer-quality gate was rerun after adding in-process
BM25 corpus reuse, selected-document row reuse, and evaluator telemetry.

| Samples | MRR | Recall@8 | Expected citation coverage | Quality pass | Faithfulness | Runtime |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 40 | 0.934 | 1.000 | 1.000 | 1.000 | 0.995 | `274.3s` |

The previous recorded strict gate runtime was `310.8s`, so this is a roughly `11.7%`
local reduction with no regression in the measured answer-quality gate. The final
telemetry run reported selected-document row cache `37` hits / `3` misses and BM25
corpus cache `37` hits / `3` misses / `0` evictions.

This is not the end of Job 4. It is the first runtime block. The next speed work should
profile answer orchestration and candidate scoring before adding any deeper cache.
