# Next-Version Sprint Six: Claim-to-Span Trust Boundary

Date: 2026-09-02

## Objective

Ensure a grounded answer is trustworthy at the claim level. Every substantive
answer claim must cite a selected retrieval context span, and the cited span
must contain enough lexical support for the claim. Missing or weak support
causes an abstention with a recovery path.

This is a runtime safety contract, not a ranking score. Retrieval quality and
answer quality metrics remain useful, but a high retrieval score cannot override
an unsupported final claim.

## Implemented Boundary

The synthesis service now records:

- claim_span_state: supported, unsupported, or unchecked.
- claim_span_claims_checked: substantive claims inspected.
- claim_span_coverage: supported claims divided by checked claims.
- claims_without_spans: claims that have no valid selected-context citation.
- claim_span_unsupported_claims: cited claims whose source support is weak.

The evidence gate blocks the answer when a substantive claim has no source span
or its cited span fails the existing support threshold. The abstention message
also points users toward narrower questions, source inspection, and OCR retry
when the input is scanned.

Generated headings, recovery notes, and diagram metadata are structural output;
answer prose and bullets remain subject to the claim-to-span check.

## Frozen Blind Holdout Procedure

Use 20-30 documents that were not used for prompt, retrieval, OCR, or threshold
tuning. Keep the documents and labels outside Git when they are copyrighted or
user-provided.

1. Copy the source documents into a local ignored directory such as
   temp/blind_holdout_sources/.
2. Create a JSONL label file in temp/ with id, source_file, query,
   answerability, and expected retrieval concepts or phrases.
3. Record SHA-256 hashes for the source files and label file before running the
   evaluation. Do not change the holdout after looking at failures.
4. Run the full local query path:

~~~powershell
pwsh -File scripts/eval_answer_quality.ps1 -Dataset temp\blind_holdout.jsonl -MetricsOutput temp\blind_holdout_metrics.json -FailuresOutput temp\blind_holdout_failures.jsonl
~~~

5. Review answerable and unanswerable cases separately. For answerable cases,
   check retrieval, citation correctness, claim-span support, and answer quality.
   For unanswerable cases, check useful abstention and absence of unsupported
   claims.
6. Keep the dataset frozen for the release comparison. Any changed label or
   source starts a new holdout version.

## Minimum Release Signals

Report these separately:

- Claim-span pass rate on answerable answers.
- Useful-abstention rate on unanswerable questions.
- Unsupported-claim count.
- Citation correctness and expected citation coverage.
- Recovery rate after source selection or OCR retry.
- Median and p95 time to a trustworthy answer.

The existing tracked evaluation files are regression fixtures, not an unseen-source
benchmark. The older heldout_longform_precision.jsonl set is a same-source
fresh-query holdout and must be described that way.

## Remaining Risk

The current check treats a selected retrieval chunk as the source span. Exact
character offsets, OCR confidence, table cells, and diagram regions are not yet
first-class evidence spans. The next hardening step is to carry page-local
offsets and extraction confidence from ingestion through retrieval and into
citation metadata.