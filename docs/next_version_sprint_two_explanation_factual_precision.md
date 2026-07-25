# Next-Version Sprint Two: Explanation and Factual Precision

Status: complete for the current reliability slice.

Date: 2026-07-25

## Objective

Improve query understanding and grounded fallback answers for generic explanation,
mechanism, and factual lookup prompts without changing the public API, adding a cloud
dependency, or tuning to one textbook.

## Changes

- Extract subjects from generic focus phrases such as `central idea behind PCA` and
  `reported for the base Transformer model`.
- Preserve operation noun phrases in mechanism plans, so prompts such as `perform
  multiclass classification` retain the requested operation instead of only the model
  name.
- Add bounded, document-agnostic query expansion for hardware, devices, processors,
  training duration, steps, hours, and runtime terms.
- Add optional factual evidence obligations without requiring factual sentences to look
  like definitions.
- Add a citation-preserving generic factual fallback for measurement and configuration
  facts that do not match the specialized date or edition patterns.
- Keep the fallback extractive: it ranks readable source sentences, prefers measurement
  cues, emits no more than three bullets, and preserves source anchors for verification.

## Why This Is Safe

The change improves evidence selection and citation repair; it does not ask a larger
model to guess harder. Specialized date and edition extraction remains unchanged. The
new path is enabled only for factual vocabulary and returns no answer when no supported
source sentence can be selected.

## Verification

Focused unit tests:

- `117 passed` across answer planning, retrieval query policy, synthesis query terms,
  query intent, and fallback quality tests.

Full local generalization gate:

- Command: `npm.cmd run eval:generalization-gate`
- Result: `PASS`
- Dataset: `110` reviewed full-query cases from `14` source files.
- Categories: `18`, including `10` unanswerable cases.
- Mode: BM25-only, low-memory, Ollama/vector/reranker disabled.
- Runtime: `431.783 s`.
- MRR: `0.903`.
- Recall@8: `0.940`.
- Expected citation coverage: `0.940`.
- Answer-quality pass rate: `0.955`.
- Overall answer score: `0.946`.
- Answer relevance: `0.854`.
- Concept coverage: `0.876`.
- Query focus: `0.802`.
- Readability: `0.990`.
- Faithfulness: `0.998`.
- Answerability correctness: `1.000`.

The validated candidate artifacts are under
`temp/generalization-gate-eval/`. In the managed Windows environment, publishing the
optional copies under `data/processed/eval/` still emits access-denied warnings; this
does not invalidate the gate or alter the RAG result.

## Remaining Work

The gate remains green, but this slice is not a claim of universal arbitrary-document
accuracy. The remaining quality failures are concentrated in explanation and source
phrase retrieval:

- multi-head attention rationale;
- reducing dimensionality rationale;
- CNN explanation;
- PCA central idea;
- dropout and DBSCAN mechanism passages;
- prompt-engineering limitation wording;
- local edition/date wording in the expanded quality rubric.

The next safe improvement is section-aware candidate retrieval and answer planning for
long textbook passages. It should be evaluated on unseen sources and fresh user-like
queries before any threshold or fallback rule is changed.

## Files Changed

- `apps/api/app/domain/answer_intelligence.py`
- `apps/api/app/services/retrieval_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/unit/test_answer_intelligence.py`
- `apps/api/app/tests/unit/test_planned_fallback_quality.py`
- `apps/api/app/tests/unit/test_retrieval_query_policy.py`
- `apps/api/app/tests/unit/test_synthesis_query_terms.py`
