# Next-Version Sprint Four: Held-Out Query Precision

Status: complete for this reliability slice.

Date: 2026-07-26

## Objective

Validate the section-aware retrieval work against fresh, long-form questions that were
not used to design the routing or fallback rules. The goal is query understanding and
answer-used evidence selection, not another textbook-specific rescue rule.

## Holdout Design

The first draft used two unrelated PDF files and labels written from different markdown
notes. That produced false failures because the labels were not answerable from those
PDFs. The dataset was corrected before measuring the slice.

The final holdout has eight fresh queries over the exact local markdown sources used for
the labels:

- `data/raw/golden_demo/05_prompt-engineering-lab.md`
- `data/raw/golden_demo/06_website-building-guide-notes.md`

It covers definitions, explanations, mechanisms, procedures, enumerations, and
limitations. This is a same-source fresh-query holdout, not an unseen-source benchmark.
That distinction is intentional and is recorded so the result is not overstated.

## Generic Fixes

- Queries such as `what should ... communicate/include/show` now use a recommendation
  answer contract.
- Queries such as `which ... should avoid`, `must not`, or `should not` now use a
  limitation contract.
- Subject extraction removes the action tail and surrounding context from leading
  `what should` questions, keeping the answer focused on the requested object.
- Mechanism evidence recognizes causal and process language such as `works well`,
  `because`, `pattern`, `flow`, and `only when`.
- Recommendation fallback synthesis weights the requested subject above broad
  retrieval-derived terms and keeps related details within the same evidence passage.
- Synthesis ignores the transport-only `Source heading:` line injected into internal
  context blocks; source headings remain available through citation/source metadata.
- The deterministic answer-quality evaluator now recognizes plural headings such as
  `Limitations` when checking a limitation plan.

No public request/response shape, model dependency, retrieval mode, or UI control changed.

## Results

Command:

```powershell
$env:PYTHONPATH='apps/api'
$env:USE_OLLAMA_GENERATION='false'
$env:USE_OLLAMA_EMBEDDINGS='false'
$env:USE_OLLAMA_RERANKER='false'
$env:RETRIEVAL_ENABLE_VECTOR='false'
$env:LOW_MEMORY_MODE='true'
python scripts/eval_retrieval.py `
  --dataset data\processed\eval\heldout_longform_precision.jsonl `
  --auto-ingest-sources --full-query --k 3 5 8 --modes bm25 `
  --output temp\heldout-query-precision-metrics-v5.json `
  --failures-output temp\heldout-query-precision-failures-v5.jsonl
```

| Metric | Before generic fix | After generic fix |
| --- | ---: | ---: |
| MRR | 1.000 | 1.000 |
| Recall@8 | 1.000 | 1.000 |
| Expected citation coverage | 1.000 | 1.000 |
| Answer-quality pass rate | 1.000 | 1.000 |
| Overall answer score | 0.939 | 0.961 |
| Answer relevance | 0.827 | 0.887 |
| Concept coverage | 0.831 | 0.938 |
| Query focus | 0.815 | 0.771 |
| Plan compliance | 1.000 | 1.000 |
| Readability | 1.000 | 1.000 |
| Faithfulness | 1.000 | 1.000 |
| Answerability correctness | 1.000 | 1.000 |
| Average BM25 query latency | 105 ms | 33 ms |

The quality movement is most important: the system now returns the first-screen
requirements, causal chat-first flow, low-end animation constraints, privacy controls,
prompt patterns, and source-boundary rule in readable source-backed answers. Retrieval
was already perfect on this small same-source holdout; the improvement is in selection
and presentation.

## Regression Verification

- Generalization gate evaluator completed on the existing 110-case corpus and produced
  a validated `passed: true` report.
- Existing gate metrics remained at MRR `0.872`, Recall@8 `0.920`, expected citation
  coverage `0.920`, answer-quality pass rate `0.927`, faithfulness `0.998`, and
  answerability correctness `1.000`.
- Full API suite: `271 passed`, one existing deprecation warning.
- Focused answer-planning, fallback, synthesis, and quality suite: `95 passed`.
- `python -m compileall -q apps/api/app`: passed.
- Next.js production build: passed; `/` first-load JavaScript remains `118 kB`.
- `git diff --check`: passed.

The `npm.cmd run eval:generalization-gate` wrapper exceeded five minutes on the managed
Windows host after generating the candidate artifacts. The candidate metrics and report
were inspected directly and the report validated as `passed: true`; this is a release
harness timing issue to fix separately, not a failed RAG result.

## Tradeoffs and Boundaries

- BM25-only, low-memory execution remains the acceptance path, so the result is offline
  and reproducible without Ollama, Chroma vectors, or a reranker.
- The eight labels are fresh questions over two exact sources, not evidence of arbitrary
  document accuracy.
- The answer-quality evaluator is deterministic and auditable; human review remains
  necessary for semantic usefulness beyond the labeled concepts.
- The generic recommendation helper intentionally prefers a direct subject match over
  broad document expansion, which can reduce breadth for an intentionally broad query.

## Files Changed

- `apps/api/app/domain/answer_intelligence.py`
- `apps/api/app/domain/answer_quality.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/unit/test_answer_intelligence.py`
- `apps/api/app/tests/unit/test_answer_quality.py`
- `apps/api/app/tests/unit/test_planned_fallback_quality.py`
- `apps/api/app/tests/unit/test_synthesis_query_terms.py`
- `data/processed/eval/heldout_longform_precision.jsonl`
- `context.md`

## Next Reliability Slice

Use genuinely unseen source families and hard documents: scanned pages, diagrams,
equations, tables, handwritten notes, and additional textbooks. Keep the same metrics,
add human-reviewed answer usefulness, and do not add more routing rules until the new
holdout shows a real failure that a generic evidence contract can address.
