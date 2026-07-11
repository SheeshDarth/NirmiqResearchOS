# Retrieval Evaluation Plan: RAG Reliability Phase

## Goal
Improve real-world academic retrieval precision before adding heavier graph, agent, or cloud model features.

The current golden demo proves the end-to-end flow. The RAG Reliability Phase focuses on harder textbooks, notes, and papers where weak evidence selection still causes broad or hallucinated answers.

Baseline before reliability work:

- BM25 MRR: `0.578`.
- Recall@8: `0.750`.
- Citation expected coverage: `0.750`.

## Metrics
- Recall@K (`K=3,5,8,20`)
- MRR for known-answer question sets
- nDCG@K for multi-evidence questions
- Citation coverage rate
- Expected citation coverage against phrase/page labels
- Full-query expected citation coverage must score full cited chunk text, not truncated UI citation excerpts
- Unsupported claim rate
- Abstention correctness
- Retrieval latency
- Generation latency
- Summary cache-hit latency
- Memory behavior on low-end/no-Ollama mode
- Abstention precision (when retrieval confidence is low)
- Grounded-answer metrics when running the full query path:
  - grounded response rate
  - abstention rate
  - citation anchor rate
  - average grounding score
  - average citation count
  - grounding state distribution

## Dataset Strategy
- Start with local textbooks, lecture notes, papers, and exam PDFs.
- Use `data/processed/eval/query_agnostic_rag_categories.jsonl` as the first query-category seed instead of mandatory hand-picked regression prompts.
- Cover definitions, explanations, comparisons, procedures, limitations, image/diagram requests, summaries, exam answers, paper drafting, and unanswerable prompts.
- Grow the real-world eval labels from `17` to at least `40` in the first reliability pass.
- Convert repeated `Needs work` feedback into candidate eval records.
- Build 40-80 manually labeled QA pairs with expected source chunks, pages, or evidence phrases.
- Store labels in local JSONL under `data/processed/eval/`.
- Supported label schema:
  - `query: string`
  - `expected_document_ids: string[]`
  - `expected_chunk_ids: string[]` (optional, preferred when available)
  - `expected_phrases: string[]` (preferred for real-world PDFs where chunk ids may change)
  - `expected_pages: number[]` (optional)
  - `answerable` or `answerability` for answerable, partial, and unanswerable cases
  - `failure_reason: string` (for promoted `Needs work` cases)

## Evaluation Loop
1. Run ingestion for corpus.
2. Execute benchmark queries.
3. Measure BM25-only, vector-only, hybrid+RRF, hybrid+RRF+rerank.
4. Inspect retrieval diagnostics for failed cases:
   - section candidates,
   - chunk-selection reasons,
   - lexical/vector/section hit state,
   - final rank and quality score.
5. Tune section-first retrieval, metadata extraction, query expansion, `K` budgets, and rerank cutoffs.
6. Freeze defaults in `app/core/config.py`.
7. Use `scripts/eval_retrieval.py` for repeatable local metrics output.
8. Compare `--modes hybrid bm25 vector` to monitor mode-wise gains/regressions.
9. Use `--full-query` when evaluating synthesis path, grounding metadata, citation coverage, and abstention.

## Exit Criteria
- Recall@8 improves from about `0.750` to at least `0.850`.
- MRR improves from about `0.578` to at least `0.700`.
- Expected citation coverage improves from about `0.750` to at least `0.900`.
- Golden demo metrics do not regress.
- BM25-only mode remains usable without Chroma, reranker, or Ollama.
- Abstention behavior is predictable and documented.
- Full-query grounding metrics stabilize across runs and make regressions visible.
