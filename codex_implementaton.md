# Codex Implementation Log

Last updated: 2026-06-06

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
- User-facing GitHub name: NIRMIQ ResearchOS.
- Positioning: offline-first academic document intelligence workspace for grounded research, chat, paper drafting, and exam preparation.
- Ecosystem note: this product remains independently useful while fitting under the broader NIRMIQ ecosystem.

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
- Added citation-faithfulness verification and fallback rewrites.
- Added chunk quality scoring and retrieval quality weighting.
- Added local ingestion privacy allowlists and upload content sniffing.
- Added adaptive generation temperature for long-context deep research.
- Added V3.1 summary caching, deterministic intent routing, and compact trust metadata.
- Added V4 Paper Lab foundation with related-work matrix, citation clusters, outline metadata, and Markdown copy export.
- Added V4 publish readiness endpoint, smoke script, README refresh, and publish checklist.

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
- Keep direct local-path ingestion restricted to trusted corpus roots by default.
- Use higher-temperature local generation only for long-context deep research/drafting while preserving citation verification.
- Cache repeated selected-document summaries until the source content hash changes.
- Show one compact answer trust badge rather than exposing raw debug metadata by default.
- Use Paper Lab for grounded research-paper scaffolds that can be copied as Markdown.
- Use `/health/readiness` and `scripts/publish_smoke.ps1` before public demo/publish.
- Treat FastAPI as the local backend runtime, not a cloud API dependency.
- Keep ChatGPT/OpenAI account usage as a future optional add-on only.

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
- `docs/security.md`
- `docs/accuracy_precision_audit.md`
- `docs/local_agent_plan.md`

Avoid re-reading the full chat unless the user asks for historical details not captured in these files.

## V4 Preparation Notes

- Build stronger Paper Lab flows: outline, related-work matrix, citation clustering. Initial V4 foundation completed.
- Build stronger Exam Lab flows: marks-based templates, question-bank ranking, diagram-aware study guides.
- Add summary caching.
- Add secure purge/export controls.
- Add deterministic intent routing and the local agent tool registry.
- Add user-owned API key support only after clear consent UI and provider boundary.

## Latest V3 Hardening Work

Date: 2026-06-02

- Restricted direct local-path ingestion to `LOCAL_INGEST_ALLOWED_ROOTS`.
- Added `SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS=false` as the safe default.
- Added lightweight upload signature/readability checks for PDF, images, and text/Markdown files.
- Exposed generator temperature settings:
  - `GENERATOR_TEMPERATURE_GROUNDED=0.15`
  - `GENERATOR_TEMPERATURE_LONG_CONTEXT=0.85`
- Routed long-context deep research, Paper Lab, and study-guide synthesis through the long-context temperature only when enough evidence is retrieved.
- Added `docs/local_agent_plan.md` for a safe local free-of-cloud-token-cost agent design.

## Latest V3.1 Reliability Work

Date: 2026-06-06

- Added `document_summaries` SQLite cache.
- Added deterministic query intent routing.
- Added citation coverage metadata.
- Updated the UI answer trust badge to `Verified`, `Rewritten`, `Needs review`, or `Low citation coverage`.
- Added tests for summary cache, intent routing, citation coverage, and cache invalidation behavior.

Verification:

- Backend unit/integration suite: `25 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

## Latest V4 Foundation Work

Date: 2026-06-06

- Added deterministic Paper Lab artifact generation from retrieved chunks.
- Paper draft responses now expose `retrieval_meta.paper_lab` with source count, evidence count, citation clusters, related-work matrix, and suggested outline.
- Added Paper Lab right-rail panel for outline and related-work matrix.
- Added `Copy Markdown Draft` for grounded paper exports using the answer, matrix, outline, and citations.
- Added unit and integration tests for Paper Lab artifacts.

Verification:

- Backend unit/integration suite: `26 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

## Latest V4 Publish Readiness Work

Date: 2026-06-06

- Added API readiness endpoint for publish/demo state.
- Added publish smoke script.
- Rewrote README for current V4 capabilities.
- Added publish checklist and updated API contract.

Verification:

- Backend unit/integration suite: `27 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

## Latest Offline-First Clarification

Date: 2026-06-06

- Clarified local backend versus cloud API language.
- Readiness now reports that cloud API access is not required.
- Smoke script now verifies `cloud_api_required=false`.
- Updated docs to make ChatGPT/OpenAI-linked usage optional and non-primary.

Verification:

- Backend unit/integration suite: `29 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

## Latest GitHub README Positioning Work

Date: 2026-06-06

- Rewrote the GitHub README around NIRMIQ ResearchOS and the promise: upload, understand, verify, learn.
- Preserved the implemented V4 feature truth instead of presenting older planned-only phase language.
- Clarified offline-first behavior, local backend status, no cloud API requirement, and future opt-in connected model boundaries.
- Updated PRD/TRD/UI handoff references so future Codex work treats ResearchOS as the GitHub-facing product name.
- Left runtime/UI renaming for a separate pass to avoid destabilizing the working preview.
- Commit: `3110de0` - Update ResearchOS GitHub positioning.

## Latest Low-Memory Runtime Hardening

Date: 2026-06-06

- Added bounded Ollama runtime settings for local generation: keep-alive, context window, prediction cap, optional GPU layer cap, and optional CPU thread cap.
- Added batched Ollama embeddings to reduce indexing memory spikes.
- Added readiness metadata for the active low-memory runtime profile.
- Added `apps/api/.env.example` and `docs/local_model_optimization.md` for RTX 4050-friendly local model setup and quantized/GGUF guidance.
- Updated README, API contract, architecture, debugging, PRD/TRD, and accuracy audit docs.
- Added unit tests for runtime payload options and embedding batching.

Verification:

- Backend unit/integration suite: `31 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.
- `git diff --check`: passed.
- Commit: `6e53767` - Add low-memory local model runtime profile.
