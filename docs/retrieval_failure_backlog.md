# Retrieval Failure Backlog

Last updated: 2026-07-07

Source file: `data/processed/eval/real_world_retrieval_failures.jsonl`

Purpose: track concrete bad retrieval cases from real-world academic material so accuracy work is guided by evidence instead of intuition.

## Current Diagnostic Snapshot

Generated from:

```powershell
.\scripts\eval_real_world.ps1
```

Baseline metrics remain unchanged:

- Hybrid MRR: `0.490`
- Hybrid Recall@8: `0.750`
- Hybrid expected citation coverage: `0.750`
- BM25 MRR: `0.578`
- BM25 Recall@8: `0.750`
- BM25 expected citation coverage: `0.750`

Failure log summary:

- Weak retrieval records: `13`
- Hybrid records: `7`
- BM25 records: `6`
- Missed at 8: `8`
- Late hit rank 4: `3`
- Late hit rank 6: `2`

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

Priority order:

1. Add normalized phrase matching to eval diagnostics.
2. Add chunk-type penalty for index/glossary/table-of-contents noise.
3. Add deterministic query expansion for academic synonyms and section terms.
4. Improve section-first retrieval candidate ranking.
5. Expand real-world eval labels from `16` toward `40`.

## Acceptance Target

The next reliability pass should move:

- Recall@8 from `0.750` to at least `0.850`.
- MRR from `0.578` to at least `0.700`.
- Expected citation coverage from `0.750` to at least `0.900`.

