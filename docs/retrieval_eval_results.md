# Retrieval Evaluation Results

Date: 2026-07-07

## MegaSprint One Query-Category Eval Seed

Date: 2026-07-09

Dataset:

```text
data/processed/eval/query_agnostic_rag_categories.jsonl
```

Purpose:

- Measure behavior by query type instead of mandatory hand-picked regression prompts.
- Covers definitions, explanations, comparisons, procedures, limitations, image/diagram requests, summaries, exam answers, paper drafting, and unanswerable prompts.
- Includes `answerability` labels so future full-query evaluation can separately score direct answers, partial evidence, and abstention correctness.

Status:

- Seed file added and smoke-tested with BM25 retrieval.
- Current small-seed BM25 smoke result: MRR `1.000`, Recall@8 `1.000`, citation expected coverage `1.000`.
- This is not a broad accuracy claim; it only confirms that the category harness and literal labels are working.
- Full metric confidence requires more real textbook/notes/paper labels.

Dataset: `data/processed/eval/demo_academic_qa.jsonl`

Sources:

- `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`
- `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`

Scope:

- 30 sample questions.
- Phrase-level expected evidence labels.
- Covers RAG retrieval, citation expectations, hallucination control, retrieval metrics, exam answer formatting, study-guide behavior, diagram policy, offline privacy, and local data controls.

## Latest Local Results

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\load_demo_dataset.ps1 -ForceReindex
.\scripts\eval_demo_dataset.ps1
```

Results:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | nDCG@5 | nDCG@8 | Citation Expected Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 30 | 0.983 | 1.00 | 1.00 | 1.00 | 0.869 | 0.861 | 0.861 | 1.00 |
| BM25 | 30 | 0.983 | 1.00 | 1.00 | 1.00 | 0.859 | 0.852 | 0.852 | 1.00 |

Interpretation:

- Hybrid retrieval ranked the first relevant evidence earlier than BM25 on this expanded dataset.
- Both modes found expected evidence within the top 3 chunks for every sample question.
- Phrase-level citation expected coverage is 1.0, meaning at least one retrieved/cited source matched the expected evidence phrase for every query.

Limitations:

- This is a compact recruiter/demo dataset, not a full benchmark.
- The PDFs are synthetic and intentionally compact so reviewers can index them quickly.
- A real-world seed set now exists, but it is still small and should grow before claims are made about broad academic accuracy.

## Baseline Before RAG Reliability Work

The RAG Reliability Phase starts from the harder real-world seed set below, not from the golden demo score.

Original baseline before the first reliability slice:

- BM25 MRR: `0.578`.
- Recall@8: `0.750`.
- Citation expected coverage: `0.750`.

Current result after deterministic query expansion, normalized eval matching, and retrieval noise penalties:

- BM25 MRR: `0.781`.
- Recall@8: `0.875`.
- Citation expected coverage: `0.875`.

The first reliability slice reached the original MRR and Recall@8 targets on the 16-sample seed, but citation coverage still needs to reach `0.900+` on a larger eval set. The next fix should continue improving evidence precision rather than increasing model size, temperature, or context length.

## Real-World Academic Seed Results

Date: 2026-07-07

Dataset: `data/processed/eval/real_world_academic_seed.jsonl`

Sources:

- `data/raw/attention_is_all_you_need.pdf`
- `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
- `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`

Note: these source PDFs are intentionally local/untracked because public repositories should not commit private or copyright-sensitive academic material. The labels and metrics are committed; replace the `source_file` paths with local documents to reproduce or expand the benchmark.

Scope:

- 16 phrase-labeled questions.
- Covers a real research paper, a full ML textbook PDF, and local GenAI notes.
- Uses `source_file` labels plus `--auto-ingest-sources`, so document IDs do not need to be manually copied.

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\eval_real_world.ps1
```

The real-world script now also writes weak retrieval records to:

```text
data/processed/eval/real_world_retrieval_failures.jsonl
```

Human-readable analysis lives in [`retrieval_failure_backlog.md`](retrieval_failure_backlog.md).

Results:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | nDCG@5 | nDCG@8 | Citation Expected Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 16 | 0.655 | 0.813 | 0.813 | 0.875 | 0.463 | 0.463 | 0.476 | 0.875 |
| BM25 | 16 | 0.781 | 0.875 | 0.875 | 0.875 | 0.544 | 0.544 | 0.544 | 0.875 |

Interpretation:

- This result is intentionally more realistic and less polished than the golden demo score.
- BM25 slightly beats hybrid on this seed set because Ollama embeddings are disabled in the low-memory/offline profile and exact academic terms dominate these labels.
- Recall@8 and citation expected coverage at `0.875` show meaningful improvement, but the seed is still small and should grow before making broad academic accuracy claims.

Next tuning targets:

- Add 40-80 more labels across textbooks, lecture notes, scanned PDFs, and research papers.
- Track which questions fail because of parsing noise versus retrieval ranking.
- Tune summary/factual expansion and source diversity using this harder set instead of only the golden demo.

## Full-Query Real-World Evaluation

Date: 2026-07-06

Command:

```powershell
.\scripts\eval_real_world.ps1 -FullQuery
```

Full-query outputs are written separately from raw retrieval outputs:

- `data/processed/eval/real_world_full_query_metrics.json`
- `data/processed/eval/real_world_full_query_failures.jsonl`

Important correction:

- Full-query evaluation now scores expected phrases against the full cited chunk text.
- The earlier diagnostic used truncated UI citation excerpts and undercounted support.
- UI excerpts remain compact, but evaluator coverage must use full source text.

Results:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | Citation expected coverage | Grounded response rate | Abstention rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 16 | 0.646 | 0.813 | 0.813 | 0.813 | 0.813 | 0.938 | 0.063 |
| BM25 | 16 | 0.667 | 0.875 | 0.875 | 0.875 | 0.875 | 0.938 | 0.063 |

Interpretation:

- The answer layer is no longer as broken as the truncated-preview metric suggested.
- BM25 full-query coverage now matches raw BM25 retrieval coverage on this seed.
- Hybrid full-query still trails raw hybrid retrieval slightly, so answer-used citation selection remains active reliability work.
- The new evidence reliability gate blocks low-citation-coverage answers instead of always returning `grounded=true`.

## Metrics Definitions

- Recall@K: whether expected evidence appears within the top K retrieved chunks.
- MRR: rewards placing the first expected evidence chunk earlier.
- nDCG@K: rewards ranking multiple expected evidence phrases near the top.
- Citation expected coverage: whether returned evidence/citations contain expected support.
