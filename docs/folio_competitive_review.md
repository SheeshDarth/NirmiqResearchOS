# NIRMIQ vs Folio Competitive Review

Last updated: 2026-06-11

## Reference Checked

- Public project: `kartikdubey17/FOLIO`
- Release checked: `v0.1.0`
- Release positioning: personal offline AI document assistant for PDF upload, local Q&A, privacy, lightweight Tauri desktop runtime, and offline usage.

## What Folio Proves

Folio validates that the market wants a simple local document assistant:

- Upload a PDF.
- Ask questions.
- Keep documents local.
- Avoid cloud dependence.
- Package as a lightweight desktop app.

## Where NIRMIQ Must Be Sharper

NIRMIQ should not compete as another generic PDF chatbot. The stronger position is:

- Source-grounded academic answers with visible citations.
- Abstention when uploaded material does not support the question.
- Deep Research evidence trail with chunk/page inspection.
- Paper Lab for citation-backed academic drafting.
- Exam Lab for marks-oriented answers, question-bank workflows, diagrams, and printable outputs.
- Golden demo benchmark that can be repeated by reviewers.
- Local-first runtime with clear proof that a cloud API is not required.

## EOD Shipping Decision

Do not add heavy desktop packaging before the web/local runtime is airtight. For this sprint:

- Add a one-command local launcher.
- Keep the app browser-based for now.
- Make the reviewer path obvious.
- Preserve the offline-first contract.
- Document the competitive positioning clearly.

## Later Desktop Packaging

If NIRMIQ needs parity with Folio's installer experience, add a Tauri shell later only after:

- Backend startup is fully scripted.
- Local model paths are documented.
- Data directories are configurable.
- Demo mode is stable.

This should be a packaging layer, not a rewrite.
