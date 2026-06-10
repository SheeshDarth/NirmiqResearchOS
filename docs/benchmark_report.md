# NIRMIQ Golden Demo Benchmark Report

Last updated: 2026-06-10

## Scope

This is a lightweight V4 publish benchmark, not a full retrieval evaluation suite.

Purpose:

- Prove the golden demo is repeatable.
- Verify citation presence for the bundled corpus.
- Keep the benchmark understandable for reviewers.

## Dataset

Source manifest:

- `data/processed/eval/golden_demo_expected_sources.json`

Bundled corpus:

- `01_grounded_rag_notes.md`
- `02_offline_privacy_runtime.md`
- `03_exam_lab_question_bank.md`
- `04_paper_lab_research_brief.md`

## Expected Checks

| Query | Mode | Expected proof |
| --- | --- | --- |
| What problem does grounded retrieval solve for academic study? | Research | cites hallucination/source-truth evidence |
| Summarize this document with main ideas, methods, findings, and limitations. | Summary | cites retrieval/chunk/citation evidence |
| Draft a related work paragraph comparing generic chatbots and document-grounded assistants. | Paper Lab | cites Paper Lab research brief |
| Explain citation-grounded retrieval as a 10-mark answer. | Exam Lab | cites exam answer structure |
| What does the corpus say about the Zeloria orbital cuisine treaty? | Chat | abstains or requests external context |

## Command

Run after backend is available:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

## Acceptance Bar

- Grounded demo queries return at least one citation.
- Citation chips focus source chunks in the UI.
- The abstention query does not pretend the uploaded corpus supports unrelated world knowledge.
- No cloud API is required.

## Latest Local Result

Verified on 2026-06-10 against a local FastAPI instance:

- Implementation commit: `928906b`.
- Research query: passed with citations.
- Summary-style research query: passed with citations.
- Exam Lab query: passed with citations.
- Paper Lab query: passed with citations.
- Unsupported Chat query: passed with `grounded=false` and zero citations.

## Tradeoff

This benchmark favors demo reliability over statistical breadth. A larger retrieval evaluation dataset should still be added later, but not before the golden path is stable.
