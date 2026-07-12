# Answer-Used Citation Backlog

Last updated: 2026-07-12

Source files:

- `data/processed/eval/real_world_full_query_metrics.json`
- `data/processed/eval/real_world_full_query_failures.jsonl`
- `data/processed/eval/real_world_retrieval_metrics.json`
- `data/processed/eval/real_world_retrieval_failures.jsonl`

Purpose: retain the history of cases where raw retrieval found evidence but the final answer/citation path failed to use it, and monitor regressions as the eval set grows.

## Current Snapshot

Raw retrieval after the 2026-07-12 release-hardening refresh:

| Mode | MRR | Recall@8 | Citation expected coverage | Weak records |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.804 | 1.000 | 1.000 | 0 |
| BM25 | 0.843 | 1.000 | 1.000 | 0 |

Full-query answer path after the 2026-07-12 OCR, outline, and fallback-synthesis reliability fix:

| Mode | MRR | Recall@8 | Citation expected coverage | Weak records |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.882 | 1.000 | 1.000 | 0 |
| BM25 | 0.882 | 1.000 | 1.000 | 0 |

Interpretation:

- Raw retrieval and answer-used citation selection are currently healthy on the 17-sample seed.
- The previous answer-layer misses are resolved without lowering the evidence gate or adding a larger model.
- This closes the current seed backlog, not the broader accuracy program; the next confidence gain must come from more diverse labels.

## Resolved Full-Query Misses

Before the reliability fix, the refreshed run exposed these four unique questions in both modes:

- `textbook-ml-001`
- `textbook-ml-003`
- `notes-genai-003`
- `notes-genai-004`

The current failure file is empty. These cases now preserve the expected answer-used evidence.

## Resolved Causes

### 1. OCR Was Normalized During Evaluation But Not Synthesis

PDF glyphs such as `Ɵ` prevented synthesis relevance checks from recognizing words such as `verification`, `sensitive`, `information`, and `retention` even though retrieval found the right chunk.

Fix shipped:

- Normalize OCR text before context relevance, directness scoring, acronym extraction, sentence splitting, and fallback synthesis.
- Keep stored source text and public API shapes unchanged.

### 2. Textbook Outlines Were Mistaken For Index Noise

The comma-density heuristic correctly rejected many backmatter fragments but also rejected legitimate chapter roadmaps and `covers the following topics` passages.

Fix shipped:

- Preserve outline passages with roadmap, part, chapter, and learning-objective cues.
- Treat `which` and `who` questions as factual lookups.

### 3. Privacy Fallback Was Product-Specific

The previous privacy fallback recognized NIRMIQ local-runtime controls but not general document controls such as PII masking, encryption, secure APIs, and retention limits.

Fix shipped:

- Generalize privacy-control extraction and remove hard-coded product claims from document answers.
- Add deterministic fact-checking terms for trusted sources, retrieval, fallback, and uncertainty.

## Next Fix Order

1. Expand the real-world eval set from `17` toward `40` across textbooks, notes, papers, and scanned PDFs.
2. Add explicit unanswerable and partial-evidence labels to measure abstention correctness.
3. Improve formatting of long outline passages without changing citation faithfulness.
4. Keep this full-query eval in the release gate and investigate any non-empty failure log before shipping.
