# MegaSprint Three Plan: Academic Workflow Depth

Last updated: 2026-07-11

## Goal

MegaSprint Three turns the simplified chat-first shell into a stronger academic workspace without making the interface complicated again.

The focus is Paper Lab, Exam Lab, diagrams, study guides, and source-grounded exports.

## Non-Negotiables

- Keep NIRMIQ offline-first and local-first.
- Preserve existing backend API shapes unless a small additive endpoint is clearly justified.
- Do not add cloud dependencies, GraphRAG, heavy agents, or a new database.
- Keep the normal UI chat-first and hide raw metadata.
- Every academic output must cite uploaded or indexed sources when evidence is available.
- If evidence is weak, the system should say so instead of drafting confident filler.

## Current Starting Point

Already available:

- Chat-first research flow.
- Upload from composer.
- Selected-source visibility.
- Readable answer body.
- Trust badges and source drawer.
- Paper Lab foundation with outline and related-work matrix.
- Exam Lab foundation with profile, question-bank import, and custom PDF generation hooks.
- Study guide rendering.
- Markdown export for current run.

Known gaps:

- Paper Lab needs stronger templates for thesis, methodology, related work, limitations, and future work.
- Exam Lab needs clearer marks-based answer formatting and better question-bank-driven generation.
- Diagram/image extraction needs to stay source-grounded and avoid pretending missing diagrams exist.
- Study guides need stronger importance ranking from source frequency, headings, and question-bank overlap.
- Exports need cleaner citation formatting and predictable filenames.

## Sprint Blocks

### Block 1: Workflow Audit And Guardrails

Purpose:

- Confirm current Paper Lab, Exam Lab, study guide, and export behavior before adding depth.

Tasks:

- Run web build and focused backend tests.
- Review existing Paper Lab and Exam Lab services/routes.
- List current output formats and weak spots.
- Add lightweight guardrails so academic tools reuse citation/trust logic from normal chat.

Acceptance:

- No normal chat regression.
- No raw metadata appears in normal workflow panels.
- Academic outputs still work when Ollama is unavailable by using grounded fallback where possible.

### Block 2: Paper Lab Templates

Purpose:

- Make Paper Lab useful for engineering students writing source-backed academic drafts.

Tasks:

- Add deterministic templates for related work, problem statement, methodology, limitations, and future work.
- Require citations per paragraph where source support exists.
- Add source diversity rules so one document or one chunk does not dominate related work.
- Keep output exportable as Markdown first.

Acceptance:

- Paper Lab answers are readable, structured, and source-backed.
- Weak evidence triggers a clear limitation note.
- Markdown export includes title, section, citations, and source list.

### Block 3: Exam Lab Answer Formats

Purpose:

- Make Exam Lab produce marks-aware, source-grounded answers.

Tasks:

- Add answer templates for 2, 5, 10, and 15 mark answers.
- Support concise, stepwise, long-form, and diagram-heavy styles.
- Use question-bank overlap to rank important questions.
- Keep answers simple enough for students to read quickly.

Acceptance:

- Exam answers include direct answer, key points, explanation, and citations when useful.
- Unsupported questions abstain or request more source material.
- Custom PDF generation uses the same grounded content rather than a separate loose path.

### Block 4: Diagram And Image Grounding

Purpose:

- Support image/diagram references without hallucinating visuals.

Tasks:

- Inventory existing parsed image/diagram artifacts.
- Add source-aware diagram references in answers when available.
- If a diagram is requested but unavailable, state that the uploaded material does not expose a usable diagram.
- Keep the first pass lightweight: no heavy vision model or external OCR dependency beyond existing tooling.

Acceptance:

- Diagram references point back to source pages or extracted artifacts.
- Missing diagrams are not invented.
- The UI stays simple and shows diagrams only when the user asks or opens sources.

### Block 5: Study Guide Builder

Purpose:

- Generate comprehensive study guides from uploaded material and optional question banks.

Tasks:

- Rank important topics from headings, repeated terms, source density, and question-bank overlap.
- Build expandable question/answer sections.
- Include diagrams when source-grounded.
- Keep citations per section rather than citation spam.

Acceptance:

- Study guide output is readable and structured.
- Each section has source support or a clear evidence warning.
- Works offline and remains usable on low-end devices.

### Block 6: Export Polish

Purpose:

- Make outputs useful outside the app.

Tasks:

- Standardize Markdown export format.
- Add predictable filenames with section, source title, and timestamp.
- Include citation list and local-first privacy note.
- Avoid leaking full local paths in normal exports unless explicitly requested.

Acceptance:

- Exported files are readable and submission/reference friendly.
- Citations are preserved.
- Local paths are sanitized by default.

## Verification Plan

Commands:

```powershell
python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q
python -m compileall apps/api/app
npm.cmd run build
```

Optional release gate:

```powershell
npm.cmd run ship:check
```

Workflow checks:

- Research: ask a conceptual query and open sources.
- Paper Lab: draft a related-work paragraph with citations.
- Exam Lab: generate a 10-mark answer from a selected source.
- Study Guide: generate a guide and verify sections are source-backed.
- Diagram request: verify real diagram references or honest abstention.
- Export: confirm citations and sanitized source metadata.

## Acceptance Criteria

- Normal chat remains simple and readable.
- Paper Lab and Exam Lab feel useful rather than placeholder-like.
- Academic outputs cite sources where needed.
- Diagram references are grounded or honestly unavailable.
- No new heavy dependencies are introduced.
- Build and focused backend verification pass before pushing.


## Sprint Progress

### 2026-07-11 Block 1 Slice: Paper Lab Guardrails

Status:

- Completed and verified.

Implemented:

- Paper Lab now selects evidence with source diversity in mind instead of blindly using the first eight chunks.
- Paper Lab artifacts now include `source_diversity`, `guardrails`, and `section_templates` for safer academic drafting.
- Paper Lab Markdown export now includes Source Grounding Notes with diversity status and safe drafting reminders.
- Unit and integration coverage were added for the new artifact behavior.

Verification:

- `python -m pytest apps/api/app/tests/unit/test_paper_lab.py -q`: passed.
- `python -m pytest apps/api/app/tests/integration/test_ingest_query_flow.py -q`: passed.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run build`: passed.

Why this matters:

- Paper Lab should help engineering students draft source-backed academic work, not overclaim from one dominant chunk or one source.
- This prepares the next slices: stronger Paper Lab templates, Exam Lab marks-aware formats, diagram grounding, and study guides.
