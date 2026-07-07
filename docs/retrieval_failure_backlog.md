# Retrieval Failure Backlog

Last updated: 2026-07-07

Source file: `data/processed/eval/real_world_retrieval_failures.jsonl`

Purpose: track concrete bad retrieval cases from real-world academic material so accuracy work is guided by evidence instead of intuition.

## Current Diagnostic Snapshot

Generated from:

```powershell
.\scripts\eval_real_world.ps1
```

Original baseline before the first reliability slice:

- Hybrid MRR: `0.490`
- Hybrid Recall@8: `0.750`
- Hybrid expected citation coverage: `0.750`
- BM25 MRR: `0.578`
- BM25 Recall@8: `0.750`
- BM25 expected citation coverage: `0.750`

Current result after deterministic query expansion, normalized eval matching, and retrieval noise penalties:

- Hybrid MRR: `0.655`
- Hybrid Recall@8: `0.875`
- Hybrid expected citation coverage: `0.875`
- BM25 MRR: `0.781`
- BM25 Recall@8: `0.875`
- BM25 expected citation coverage: `0.875`

Failure log summary:

- Weak retrieval records: `5`
- Hybrid records: `3`
- BM25 records: `2`
- Missed at 8: `4`
- Late hit rank 7: `1`

The failure log records both hard misses and late hits beyond rank 3, because late evidence is less likely to be used correctly during synthesis.

## Repeated Failure Patterns

### 1. Textbook Index And Glossary Noise

Several Hands-On Machine Learning queries retrieve index/glossary-like chunks before the relevant explanatory section.

Examples:

- `textbook-ml-003`: cross-validation workflow retrieves index chunks before the relevant cross-validation explanation.
- `textbook-ml-004`: common learning algorithms retrieves glossary/index fragments instead of the early overview.

Likely fix:

- Penalize `index`, `glossary`, and bibliography-like chunks for explanatory questions.
- Keep those chunks available for lookup, but avoid ranking them above body content for conceptual answers.

### 2. Vocabulary Mismatch

Some user-style questions use natural wording while the source uses a specific term.

Examples:

- Query: "How does the Transformer represent token positions?"
- Source phrase: "positional encodings"

Likely fix:

- Add deterministic local query expansion from headings, key terms, and known academic synonyms.
- Prefer cheap expansion before adding heavier rerankers.

### 3. Exact-Phrase Eval Brittleness

Some retrieved chunks are semantically correct but miss the exact expected phrase.

Example:

- `paper-transformer-001` retrieves "we propose the Transformer, a model architecture eschewing recurrence..." near the top.
- The expected phrase uses a slightly different wording.

Likely fix:

- Add multiple expected phrase variants for real-world labels.
- Add normalized phrase matching for punctuation, hyphenation, ligatures, and OCR artifacts.

### 4. OCR And Encoding Noise

The GenAI notes include mojibake and OCR artifacts such as malformed ligatures.

Examples:

- `sensiÆŸve`
- `informaÆŸon`
- `retenon`

Likely fix:

- Add normalization during parsing and evaluation.
- Track low-quality OCR chunks and reduce confidence when they dominate retrieval.

### 5. Broad Overview Questions Need Section Awareness

Overview queries often require the introductory section rather than isolated term hits.

Examples:

- common algorithms in early overview,
- reducing dimensionality to fight the curse of dimensionality.

Likely fix:

- Strengthen section-first retrieval for selected documents.
- Prefer chunks from overview/intro sections when the query asks for "early overview", "topics", "what does the book cover", or "main ideas".

## Next Engineering Fixes

Completed in the first reliability slice:

- Added normalized phrase matching to eval diagnostics.
- Added retrieval noise penalties for index/glossary/reference-like chunks.
- Added deterministic query expansion for common academic wording mismatches.

Next priority order:

1. Improve section-first retrieval candidate ranking.
2. Add more robust OCR/mojibake normalization during parsing.
3. Expand real-world eval labels from `16` toward `40`.
4. Add answer-used citation selection tuning after retrieval coverage stabilizes.

## Acceptance Target

The next reliability pass should preserve or improve:

- Recall@8 at or above `0.850`.
- MRR at or above `0.700`.
- Expected citation coverage from `0.875` to at least `0.900`.
