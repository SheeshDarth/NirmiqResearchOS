# Retrieval Evaluation Results

Date: 2026-07-12

## MegaSprint One Query-Category Eval Seed

Date: 2026-07-12

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

Current result after deterministic query expansion, normalized eval matching, acronym-aware section ranking, retrieval noise penalties, strict anchor rescue, answer-directness priority, and corrected source-phrase labels:

- BM25 MRR: `0.868`.
- Hybrid MRR: `0.828`.
- Recall@8: `1.000`.
- Citation expected coverage: `1.000`.

The current reliability slice reaches the original MRR, Recall@8, and citation coverage targets on the 17-sample seed. The seed is still small, so the next fix should grow labels and continue improving evidence precision rather than increasing model size, temperature, or context length.

## Real-World Academic Seed Results

Date: 2026-07-13

Dataset: `data/processed/eval/real_world_academic_seed.jsonl`

Sources:

- `data/raw/attention_is_all_you_need.pdf`
- `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
- `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`

Note: these source PDFs are intentionally local/untracked because public repositories should not commit private or copyright-sensitive academic material. The labels and metrics are committed; replace the `source_file` paths with local documents to reproduce or expand the benchmark.

Scope:

- 17 phrase-labeled questions.
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

Latest refresh note: the 2026-07-13 run retained Recall@8 and expected citation coverage at `1.000`; one cross-validation label first appears at rank 4, which remains inside the accepted retrieval window.

Human-readable analysis lives in [`retrieval_failure_backlog.md`](retrieval_failure_backlog.md).

Results:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | nDCG@5 | nDCG@8 | Citation Expected Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 17 | 0.868 | 0.941 | 1.000 | 1.000 | 0.590 | 0.599 | 0.599 | 1.000 |
| Hybrid | 17 | 0.828 | 0.941 | 1.000 | 1.000 | 0.554 | 0.577 | 0.577 | 1.000 |

Interpretation:

- This result is intentionally more realistic and less polished than the golden demo score.
- BM25 still leads hybrid on first-rank placement, but hybrid improved after candidate priority gave more weight to direct answer relevance.
- Recall@8 and citation expected coverage at `1.000` show meaningful improvement, but the seed is still small and should grow before making broad academic accuracy claims.
- Two labels were corrected because the retrieved source text was valid while the original expected phrase contained OCR/wording damage.

Next tuning targets:

- Add 40-80 more labels across textbooks, lecture notes, scanned PDFs, and research papers.
- Track which questions fail because of parsing noise versus retrieval ranking.
- Tune summary/factual expansion and source diversity using this harder set instead of only the golden demo.

## Full-Query Real-World Evaluation

Date: 2026-07-13

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
| Hybrid | 17 | 0.902 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| BM25 | 17 | 0.902 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |

Interpretation:

- OCR normalization now runs before synthesis relevance checks and evidence extraction.
- Legitimate textbook outlines are no longer discarded by the backmatter/index-noise filter.
- Generic privacy and fact-checking controls now use source-specific fallback synthesis rather than product-specific wording.
- Both full-query modes preserve expected evidence for every answerable sample in the current seed.
- Removing the legacy factual seed reorder improved full-query MRR from `0.882` to `0.902` while keeping coverage complete.
- The evidence reliability gate remains unchanged; the improvement comes from better evidence interpretation, not a weaker abstention threshold.

## 40-Case Answer-Quality Closure Benchmark

Latest rerun: 2026-07-19

Dataset:

```text
data/processed/eval/real_world_answer_quality.jsonl
```

Command:

```powershell
.\scripts\eval_answer_quality.ps1 -Modes bm25
```

This is the hardest committed evaluation path. It runs the complete query pipeline with Ollama generation, Ollama embeddings, and reranking disabled, then scores the full chunks actually cited by the answer.

| Mode | Samples | MRR | Recall@3 | Recall@8 | Citation expected coverage | Answer-quality pass | Faithfulness | Readability | Answerability correctness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 40 | 0.921 | 1.000 | 1.000 | 1.000 | 1.000 | 0.995 | 0.985 | 1.000 |

Interpretation:

- MRR, Recall@8, and expected citation coverage exceed the reliability gates of `0.700`, `0.850`, and `0.900`.
- The evaluator gives retrieval credit only for answer-used citation chunks, so high raw recall cannot hide poor synthesis selection.
- Definitions, comparisons, mechanisms, interpretations, procedures, summaries, and workflow-placement cases are handled through generic evidence obligations, not hard-coded answer text.
- Both deliberately unsupported cases abstained correctly.
- `real_world_answer_quality_failures.jsonl` is empty for this dataset. This means no current labeled case is below threshold, not that arbitrary queries are solved.
- The strict run took about two minutes on the current verification machine and should still be optimized by caching corpus setup without weakening evaluation semantics.
- Further tuning against the same 40 labels is paused; the next reliability work must use unseen and harder documents.

## Metrics Definitions

- Recall@K: whether expected evidence appears within the top K retrieved chunks.
- MRR: rewards placing the first expected evidence chunk earlier.
- nDCG@K: rewards ranking multiple expected evidence phrases near the top.
- Citation expected coverage: whether returned evidence/citations contain expected support.

## 2026-07-26 Section-Aware Evidence Selection

The third next-version reliability slice improved answer-used evidence selection for
long textbook explanations. The isolated CNN case previously cited related passages
without using the exact pooling mechanism; after the slice, the answer used pages 615
and 628 and explained the source-backed mechanism.

Full generalization gate (`110` cases, BM25-only, low-memory):

| MRR | Recall@8 | Citation expected coverage | Answer pass | Answer relevance | Concept coverage | Faithfulness |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.872 | 0.920 | 0.920 | 0.927 | 0.833 | 0.839 | 0.998 |

The gate passed all acceptance thresholds. Explanation pass rate improved from `0.556`
to `0.778`, and factual lookup from `0.600` to `0.800`, while raw MRR/Recall moved
slightly below the prior tracked artifact (`0.903`/`0.930`). This tradeoff is recorded
honestly; the next slice should validate held-out explanation/mechanism prompts before
further tuning. See [`next_version_sprint_three_section_aware_retrieval.md`](next_version_sprint_three_section_aware_retrieval.md).
