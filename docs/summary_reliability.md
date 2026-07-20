# Recursive Summary Reliability

Status: Remaining Job 3 complete on 2026-07-20.

Job 3 hardens the selected-document summary path after recursive reduction. It is a
developer-facing reliability gate; it does not add controls or metadata to the normal
chat UI and it does not change the public query contract.

## Reliability Flow

```mermaid
flowchart LR
    A["Selected-document summary"] --> B["All readable chunks"]
    B --> C["Adversarial structure checks"]
    C --> D["Recursive section/chapter reduction"]
    D --> E["Answer citation anchors"]
    E --> F["Sentence-to-excerpt support audit"]
    F --> G["Cache version and citation validation"]
    G --> H["Developer diagnostics and CI gate"]
```

## Implemented Checks

- Adversarial fixtures cover front/back matter, table-of-contents and index noise,
  duplicate OCR headings, mojibake, missing or false chapter boundaries, equations,
  tables, diagrams, and limitations.
- Every cited answer sentence is checked against the excerpt attached to its citation.
  The check is lexical and conservative: it catches wrong wiring and unsupported
  citation anchors, but it is not a semantic entailment proof.
- Summary output is checked for deterministic repeatability.
- The gate records wall-clock latency and Python allocation peak for bounded synthetic
  fixtures. It is a regression signal, not a hardware benchmark.
- Cache hits validate the recursive-summary version and citation support before the
  cached response is returned. Future summary algorithm changes must bump
  `RECURSIVE_SUMMARY_VERSION`.

## Measured Gate

The offline gate uses three adversarial cases and passes all of them:

| Check | Result |
| --- | ---: |
| Cases | `3/3` |
| Deterministic output | `3/3` |
| Citation-support coverage | `1.000` |
| Invalid citation anchors | `0` |
| Unsupported cited sentences | `0` |
| Synthetic median latency | roughly `3-7 ms` across local runs |
| Peak Python allocation | `9.7-10.5 KiB` |

The full-textbook baseline remains the Job 2 result: first recursive summary `3.783 s`
and cached repeat `0.191 s` on the locally indexed 2,842-chunk textbook. Job 3 does
not claim that synthetic fixture timings predict every PDF's runtime.

## Run It

```powershell
npm.cmd run eval:summary-reliability
```

The command runs in `temp/summary-reliability-eval`, publishes
`data/processed/eval/recursive_summary_reliability_metrics.json`, and fails closed on
non-determinism, invalid anchors, or unsupported cited sentences.

## Boundaries

- Lexical support cannot prove that a paraphrase preserves every nuance.
- OCR-heavy, legal, medical, highly visual, or very large documents still need real
  user evaluation and memory measurements.
- Whole-document summaries use the all-chunk recursive path; scoped chapter summaries
  remain query-focused RAG.
- Cache invalidation remains content-hash plus summary-version based. A version bump or
  explicit local cache purge is preferred to silently reusing stale summaries.

## Final Closure

The final five-advisor council unanimously approved closure after the cache path also
enforced selected-document scope. The validator now rejects otherwise valid citations,
active rows, or hierarchy IDs from another document. Final evidence: `246` backend tests
passed with one third-party timezone deprecation warning; Ruff, isolated compile, the
exact npm evaluation command, and the fresh Next build passed. Job 4 is unlocked.
