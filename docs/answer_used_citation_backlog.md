# Answer-Used Citation Backlog

Last updated: 2026-07-07

Source files:

- `data/processed/eval/real_world_full_query_metrics.json`
- `data/processed/eval/real_world_full_query_failures.jsonl`
- `data/processed/eval/real_world_retrieval_metrics.json`
- `data/processed/eval/real_world_retrieval_failures.jsonl`

Purpose: track where raw retrieval finds evidence, but the final answer/citation path fails to use the best evidence.

## Current Snapshot

Raw retrieval after the first reliability slice:

| Mode | MRR | Recall@8 | Citation expected coverage | Weak records |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.655 | 0.875 | 0.875 | 3 |
| BM25 | 0.781 | 0.875 | 0.875 | 2 |

Full-query answer path:

| Mode | MRR | Recall@8 | Citation expected coverage | Weak records |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.583 | 0.750 | 0.750 | 4 |
| BM25 | 0.615 | 0.750 | 0.750 | 4 |

Interpretation:

- Raw retrieval improved substantially.
- The final answer/citation layer still loses evidence.
- This is now the main quality bottleneck before increasing model size, temperature, context length, or adding heavier retrieval systems.

## Current Full-Query Misses

The current full-query failure log contains `8` missed-at-8 records:

- `paper-transformer-001`
- `paper-transformer-004`
- `paper-transformer-005`
- `textbook-ml-003`
- `notes-genai-004`

Some samples fail in both `hybrid` and `bm25`, so the unique question count is smaller than the record count.

## Likely Causes

### 1. Final Citations Do Not Always Match Top Retrieved Evidence

The answer layer returns only answer-used citations. This is correct for trust, but it means the synthesis/fallback layer must choose the strongest evidence, not just any retrieved evidence.

Fix direction:

- Score candidate evidence sentences against the user query and expected answer type.
- Prefer answer sentences from chunks with high lexical overlap, section match, and low noise penalty.
- Keep the public citations limited to actually used chunks.

### 2. Fallback Synthesis Still Uses Broad Sentences

Fallback synthesis is safer than hallucinating, but it can select broad context sentences when a narrower answer sentence exists lower in the context.

Fix direction:

- Add answer-mode-aware sentence scoring.
- Boost sentences containing expansion terms and direct query terms.
- Penalize metadata/index/reference sentences during fallback sentence selection.

### 3. Summary And Overview Logic Can Hide Specific Evidence

Some questions are broad enough that the generated answer may cite overview chunks while the expected phrase lives in a more specific chunk.

Fix direction:

- For selected-document queries, retain a small "precision evidence" pool beside the broad context pool.
- Let final citation selection pull from precision evidence even when the answer is structured as a summary.

## Next Fix Order

1. Add answer-used citation diagnostics to `retrieval_meta`.
2. Improve fallback sentence scoring with query-expansion overlap and noise penalties.
3. Ensure answer-used citations can include the strongest precision chunks, not only the first broad context chunks.
4. Re-run full-query eval and target citation expected coverage from `0.750` to `0.850+`.

