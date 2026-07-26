# Next-Version Sprint Five: Unseen OCR Source Reliability

Date: 2026-07-26

## Objective

Validate NIRMIQ on independently sourced, image-only PDFs that were not part of the
tracked synthetic hard-document fixtures, while keeping the default path local,
offline-capable, and usable without Ollama, Chroma, or a reranker.

## Local Holdout

The temporary holdout contains 12 reviewed questions across two local scan PDFs:

- A prompt-engineering scan: definitions, enumerations, mechanisms, procedures,
  limitations, and one unanswerable question.
- A website-building guide scan: enumeration, procedure, performance, comparison,
  deployment, and one unanswerable question.

The source PDFs remain local and ignored by Git. The dataset is intentionally kept in
`temp/` because these are user-local copyrighted/source files, not distributable test
fixtures. This report therefore records the result for the current machine, not a
reproducible public benchmark.

## Baseline And Result

The first baseline after OCR indexing and before the answer-side repair was:

| Metric | Baseline | Final |
| --- | ---: | ---: |
| MRR | 0.550 | **0.850** |
| Recall@8 | 0.600 | **0.900** |
| Expected citation coverage | 0.600 | **0.900** |
| Answer-quality pass rate | 0.500 | **0.833** |
| Overall answer score | 0.757 | **0.893** |
| Answer relevance | 0.514 | **0.814** |
| Concept coverage | 0.460 | **0.835** |
| Faithfulness | 0.850 | **0.967** |
| Answerability correctness | 0.833 | **1.000** |

Final run: hybrid retrieval with the deterministic offline fallback, 12 samples, 10
answerable retrieval-scored cases, average latency `1.076 s`, p95 `4.468 s`.

## Implementation

- Coalesced short same-page OCR fragments into bounded 320-token evidence blocks.
- Added narrow OCR acronym normalization for common `AI`/`A1` recognition errors.
- Added a zero-chunk cache invariant so failed OCR/index attempts cannot masquerade as
  indexed documents.
- Added bounded morphology aliases for query/document terms such as deployment/deploy,
  optimization/optimize, assets/asset, and prompting/prompt.
- Improved generic definition selection so OCR chapter prefixes do not outrank the
  subject-led definition.
- Preserved explicit enumeration counts and independently cited each list item so the
  citation verifier can validate short bullets.
- Added generic answer-side prioritization for concrete optimization and deployment
  instructions.
- Added a generic `how can` action-evidence fallback for mechanism/procedure questions.
- Kept the evidence gate fail-closed and extended verification to short cited list items.
- Added unit coverage for each new behavior.

## Residual Risk

One limitations query still exposes noisy OCR from a dense scan page. Tesseract PSM 6
or PSM 11 can recover more words on that page, but they degrade other pages when made
the global default. The safe decision is to keep PSM 3 as the default, retain the
`TESSERACT_PSM` override, and schedule per-page OCR quality selection as the next hard
document slice rather than adding document-specific answer rules.

This result is a strong held-out signal, not proof that arbitrary scans, handwriting,
tables, diagrams, or equations are solved. The tracked synthetic hard-document gate
remains the reproducible regression suite.

## Verification

- Backend unit and integration tests: `282 passed`.
- Python compile check: passed.
- Public API shape: unchanged.
- No new dependencies, cloud services, graph database, or heavy model required.

