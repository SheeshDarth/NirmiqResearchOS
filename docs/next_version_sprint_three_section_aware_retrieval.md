# Next-Version Sprint Three: Section-Aware Evidence Selection

Status: complete for this reliability slice.

Date: 2026-07-26

## Objective

Make long-document explanations use the passage that directly answers the question,
not merely a nearby passage that repeats the same topic words. The slice is designed
for offline BM25 operation first and does not change the public query API.

## Failure Reproduced

For `Explain CNN` against the local Hands-On Machine Learning textbook, BM25 could
retrieve CNN-related passages but synthesis preferred a generic architecture or
sequence example. The exact `Pooling Layers` passage on page 628 was present in the
retrieved evidence but was not used in the answer.

This was a two-stage failure:

1. Broad acronym expansion did not reliably keep component passages near the answer.
2. Synthesis ranked raw query overlap above document-local, answer-bearing evidence.

## Implementation

### Retrieval

- Production retrieval now applies document-aware expansion after acronym detection,
  rather than returning only the acronym expansion.
- Top acronym-matched sections contribute a bounded set of section-anchor terms.
- Section-component rescue keeps direct, nearby component chunks in the candidate pool
  for explanation, mechanism, procedure, and related answer plans.
- Rescued chunks receive a small structural priority bonus, with additional weight for
  generic answer-bearing cues such as `goal is to`, `works by`, and `consists of`.
- Retrieval metadata records whether section-component rescue was applied and how many
  candidates it added. This remains debug metadata and is not shown in normal UI.

### Synthesis

- Synthesis receives retrieval-derived evidence terms internally through the existing
  bundle metadata; no request or response shape changed.
- The top two retrieved chunks contribute a bounded lexical window so distinctive
  mechanism terms such as `subsample`, `shrink`, and `computational` can outrank a
  generic related example.
- Retrieved section headings are included in the internal evidence block to preserve
  document structure for the local model and fallback composer.
- Definition fallback ranks rare document-local component terms more strongly than
  terms repeated across unrelated nearby chunks.
- The final answer still passes citation verification and the existing evidence gate.

## Targeted Result

Dataset: one local CNN explanation label, BM25-only, Ollama/vector/reranker disabled.

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| MRR | 0.000 | 0.500 |
| Recall@8 | 0.000 | 1.000 |
| Expected citation coverage | 0.000 | 1.000 |
| Answer relevance | 0.650 | 0.883 |
| Concept coverage | 0.500 | 0.833 |
| Faithfulness | 1.000 | 1.000 |

The resulting answer identifies convolutional layers and explains that pooling
subsamples/shrinks feature maps to reduce computational load, with answer-used
citations to pages 615 and 628.

## Full Generalization Gate

Command:

```powershell
npm.cmd run eval:generalization-gate
```

Result: `PASS` on `110` reviewed full-query cases, `14` source files, `18` categories,
and `10` unanswerable cases using the offline BM25 path.

| Metric | Current result | Gate target |
| --- | ---: | ---: |
| MRR | 0.872 | 0.700 |
| Recall@8 | 0.920 | 0.850 |
| Expected citation coverage | 0.920 | 0.900 |
| Answer-quality pass rate | 0.927 | 0.900 |
| Overall answer score | 0.938 | 0.850 |
| Answer relevance | 0.833 | 0.750 |
| Concept coverage | 0.839 | 0.750 |
| Query focus | 0.820 | 0.700 |
| Readability | 0.989 | 0.900 |
| Faithfulness | 0.998 | 0.950 |
| Answerability correctness | 1.000 | 1.000 |

Category movement is useful: explanation pass rate improved from `0.556` to `0.778`,
and factual lookup improved from `0.600` to `0.800` against the previous tracked
gate artifact. Raw retrieval MRR/Recall moved down from `0.903`/`0.930` to
`0.872`/`0.920`, so this is not being presented as a universal improvement. The
change improves direct answer use and materially reduces evaluation runtime, but the
next slice should reduce any broad-ranking tradeoff on unseen documents.

## Verification

- Focused retrieval, answer-planning, synthesis, and fallback tests: `112 passed`.
- Python compile check passed with `PYTHONPYCACHEPREFIX` redirected to `C:\tmp`.
- Targeted CNN full-query evaluation passed with Recall@8 and citation coverage `1.000`.
- Full generalization gate passed with all acceptance thresholds satisfied.
- No cloud dependency, heavy model, graph database, agent framework, or public API
  change was added.

## Remaining Work

- The held-out explanation/mechanism and query-agnostic precision check is now recorded
  in `next_version_sprint_four_holdout_precision.md`.
- Compare section-component rescue against genuinely unseen source families, not only
  the same-source holdout and current 110-case gate.
- Improve enumeration and limitation answer selection, which remain weaker categories
  in the current failure file.
- Keep raw section/debug details behind developer/deep-research inspection only.

## Files Changed

- `apps/api/app/services/retrieval_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/unit/test_retrieval_query_policy.py`
- `apps/api/app/tests/unit/test_synthesis_query_terms.py`
- `data/processed/eval/generalization_gate_failures.jsonl`
- `data/processed/eval/generalization_gate_metrics.json`
- `data/processed/eval/generalization_gate_report.json`
- `context.md`
