# Codex Implementation Log

Last updated: 2026-05-30

Note: filename spelling follows the user request: `codex_implementaton.md`.

## Standing Project Rule

After each meaningful project work unit:

- Update `context.md`.
- Commit changes.
- Push to GitHub.

## Current Branch

- `v3-foundation`

## Product Identity

- Repository/project: NIRMIQ ResearchOS.
- User-facing name: NIRMIQ Academic Intelligence.
- Positioning: local-first academic intelligence workspace for grounded research, chat, paper drafting, and exam preparation.

## Completed Phases

### Phase 1

- Established repository architecture.
- Defined FastAPI service boundaries.
- Defined ingestion, indexing, retrieval, memory, and inference lifecycles.
- Added SQLite schema foundation.
- Added retrieval policy and clean backend layering.

### Phase 2

- Added document browsing and source drilldown.
- Improved citation cards and chunk preview readability.
- Added query/session comparison.
- Made UI more chatbot-like and less dashboard-heavy.

### Phase 3

- Shifted product from exam-only assistant to general academic intelligence.
- Added Research, Chat, Paper Lab, and Exam Lab workspace framing.
- Added ChatGPT-like upload from composer.
- Added grounded PDF summary mode.
- Added local-first landing/profile flow.
- Added NIRMIQ logo integration.
- Added compact/minimizable composer and source cockpit.
- Added printable custom PDF behavior for Exam Lab.

### Phase 4 Foundation

- Added grounding metadata and score-aware synthesis behavior.
- Added retrieval evaluation and impact planning.
- Added parse cache for repeated PDF indexing performance.

## Important Commits So Far

- `30261b7`: Compact research composer layout.
- `9e24237`: Add source cockpit and quick summary UI.
- `3a93d8f`: Add impact roadmap and PDF parse cache.
- `91117b5`: Add grounded PDF summary mode.
- `e2d9c9e`: Add chat uploads and fix scroll performance.

## Current App Capabilities

- Upload PDFs, text, Markdown, and images.
- Ingest local-path documents.
- Summarize indexed PDFs.
- Query documents with citations.
- Inspect sources and chunks.
- Use Research, Chat, Paper Lab, and Exam Lab sections.
- Generate printable custom exam PDF from the current grounded answer.
- Minimize the composer while reading responses.

## Current Verification Routine

- `npm run build` from `apps/web`.
- Backend unit/integration tests from repo root with `PYTHONPATH=apps/api`.
- Browser smoke: open `http://127.0.0.1:3002`, verify no console errors, upload/select source, summarize, inspect citations.

## Future Codex Workflow

For future sessions, read these files first:

- `context.md`
- `prd.md`
- `trd.md`
- `UI_UX.md`
- `backend_architecture.md`
- `debugging.md`
- `docs/internship_impact_plan.md`

Avoid re-reading the full chat unless the user asks for historical details not captured in these files.

## V4 Preparation Notes

- Build stronger Paper Lab flows: outline, related-work matrix, citation clustering.
- Build stronger Exam Lab flows: marks-based templates, question-bank ranking, diagram-aware study guides.
- Add summary caching and chunk quality scoring.
- Add privacy/data controls.
- Add user-owned API key support only after clear consent UI and provider boundary.

