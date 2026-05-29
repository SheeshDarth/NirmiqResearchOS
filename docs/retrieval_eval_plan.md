# Retrieval Evaluation Plan (Phase 1)

## Goal
Validate groundedness and relevance before adding advanced orchestration.

## Metrics
- Recall@K (`K=5,10`)
- MRR for known-answer question sets
- Citation coverage rate
- Abstention precision (when retrieval confidence is low)
- Grounded-answer metrics when running the full query path:
  - grounded response rate
  - abstention rate
  - citation anchor rate
  - average grounding score
  - average citation count
  - grounding state distribution

## Dataset Strategy
- Start with 20-50 curated local documents.
- Build 40-80 manually labeled QA pairs with expected source chunks.
- Store labels in local JSONL under `data/processed/eval/`.
- Supported label schema:
  - `query: string`
  - `expected_document_ids: string[]`
  - `expected_chunk_ids: string[]` (optional, preferred when available)

## Evaluation Loop
1. Run ingestion for corpus.
2. Execute benchmark queries.
3. Measure BM25-only, vector-only, hybrid+RRF, hybrid+RRF+rerank.
4. Tune `K` budgets and rerank cutoffs.
5. Freeze defaults in `app/core/config.py`.
6. Use `scripts/eval_retrieval.py` for repeatable local metrics output.
7. Compare `--modes hybrid bm25 vector` to monitor mode-wise gains/regressions.
8. Use `--full-query` when you want to evaluate the actual synthesis path and the new grounding metadata.

## Exit Criteria
- Hybrid+rerank beats single-method baselines.
- Citation coverage exceeds 90% on labeled set.
- Abstention behavior is predictable and documented.
- Full-query grounding metrics stabilize across runs and make regressions visible.
