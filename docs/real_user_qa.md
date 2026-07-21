# Real-User QA Loop

Status: Remaining Job 6 complete locally on 2026-07-21.

NIRMIQ's current benchmark gates protect the known corpus. Real users will ask messier
questions, upload noisier documents, and notice readability failures that fixed labels
do not catch. This loop turns those observations into local eval candidates without
uploading feedback anywhere.

## Goal

- Capture 10-20 natural questions per target document.
- Mark answers as `Good` or `Needs work` in the app.
- Convert local feedback into reviewable eval candidates.
- Promote reviewed failures into tracked datasets only after expected evidence is added.
- Improve retrieval and synthesis against categories, not one-off memorized prompts.

## What To Test

Use one real textbook, one research paper, and one noisy study material source when
possible.

Question categories:

- Definitions: `What is X?`
- Explanations: `Explain X in simple terms.`
- Mechanisms: `How does X work?`
- Procedures: `What are the steps for X?`
- Comparisons: `Compare X and Y.`
- Limitations: `Where does X fail?`
- Summaries: `Summarize this chapter/source.`
- Visual references: `Use the figure/table/equation if available.`
- Exam answers: `Write this as a 5/10-mark answer.`
- Paper synthesis: `Draft a paragraph with citations.`
- Unanswerable prompts: ask about something the document does not contain.

## Pass/Fail Rubric

Pass:

- The answer directly addresses the query.
- Paragraphs are easy to read before opening sources.
- Citations appear where they help verify claims.
- Source excerpts support the answer, not just keyword overlap.
- Unsupported questions produce `Not found in sources` or `Needs more evidence`.
- Metadata, scores, local paths, and chunk IDs stay hidden in the normal UI.

Fail:

- The answer is just copied keyword fragments.
- The system answers confidently from unrelated chunks.
- Citations point to passages that do not support the paragraph.
- The answer is too broad for a precise question.
- The response reads like a benchmark artifact rather than a student-facing explanation.
- The user must open debug panels to understand the result.

## Local Feedback Export

After testing in the app, run:

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run qa:real-user
```

Default local-only outputs:

- `temp/real_user_qa/local_feedback_eval_candidates.jsonl`
- `temp/real_user_qa/local_feedback_report.json`

These files are intentionally under `temp/` and should not be committed as raw user
feedback. Review them manually first.

To include both `Good` and `Needs work` records:

```powershell
npm.cmd run qa:real-user -- -IncludeGood
```

## Promotion Rules

Do not promote a feedback record directly into tracked eval data until it has:

- A scrubbed query with no private identifiers.
- A source file that is safe to use in the repo or a reproducible fixture.
- Expected evidence phrases or required concepts.
- Answerability label: `answerable` or `unanswerable`.
- Category label from the query taxonomy.
- Notes about why the previous answer failed.

Promote reviewed cases into the appropriate tracked set:

- `data/processed/eval/real_world_answer_quality.jsonl`
- `data/processed/eval/hard_document_qa.jsonl`
- Future textbook/noisy-note expansion files.

## Acceptance Target

For the next public polish pass:

- At least 20 natural questions recorded manually.
- At least 10 `Needs work` cases exported and reviewed.
- At least 5 reviewed cases promoted into tracked eval labels.
- No decline in the existing 40-case answer-quality gate.
- No private raw feedback committed.

## Boundary

This job does not claim arbitrary-document perfection. It creates the local measurement
loop needed to keep improving accuracy as real users test NIRMIQ.

## Job 6 Verification

Validated on 2026-07-21:

- Unit test for exporter classification and path-safe source labels: `2 passed`.
- Python compile for the exporter and focused test: passed with workspace pycache.
- `npm.cmd run qa:real-user`: passed and exported `2` local `Needs work` candidates
  into ignored `temp/real_user_qa`.
- `npm.cmd run build`: passed at `118 kB` first-load JavaScript.
- GitHub Actions run `29822935910`: passed, including Linux browser-mode smoke and
  backend/web release checks.

The generated feedback artifacts remain local and are not part of the committed release
state.
