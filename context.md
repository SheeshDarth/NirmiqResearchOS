# NIRMIQ Academic Intelligence System Context

Last updated: 2026-05-30
Current branch: `v3-foundation`
Repository target: `https://github.com/SheeshDarth/NirmiqAcademicIntelligenceSystem`
Current git remote may still point to the previous URL until the GitHub repository itself is renamed.
Local workspace: `C:\Nirmiq-researchOS`
Primary app URL: `http://127.0.0.1:3002/`
API URL: `http://127.0.0.1:8000/`

## Project Metadata

Project name: NIRMIQ Academic Intelligence System
Project type: Offline-first adaptive academic intelligence system
Owner/developer: Siddharth / SheeshDarth
Target user: Solo local-first researcher/student/developer
Target machine: RTX 4050 laptop class hardware
Primary branch for current work: `v3-foundation`
Stable baseline branch: `main`

## Product Direction

NIRMIQ Academic Intelligence System is a local-first document intelligence workspace for:

- Research over uploaded documents.
- General local-first chatbot behavior with abstention when no evidence exists.
- Exam preparation using uploaded notes, PDFs, textbooks, question banks, answer styles, marks, and extracted source diagrams.
- Grounded answers with citations and source inspection.
- Low-VRAM, offline-friendly operation.

The system should avoid cloud-first, enterprise, and multi-user complexity until the local MVP is strong.

## Core Technical Stack

Frontend:

- Next.js PWA-style app in `apps/web`.
- Main UI file: `apps/web/app/page.tsx`.
- Main style file: `apps/web/app/globals.css`.

Backend:

- FastAPI app in `apps/api`.
- Entrypoint: `apps/api/app/main.py`.
- Dependency container: `apps/api/app/core/deps.py`.

Storage:

- SQLite for documents, chunks, memory, sessions, exam profiles, question banks, and diagram metadata.
- ChromaDB for vector storage.
- BM25 index for lexical retrieval.

Retrieval / RAG:

- BM25 retrieval.
- Chroma vector retrieval.
- Reciprocal Rank Fusion.
- Lightweight reranking abstraction.
- Context packing and citation-aware synthesis.
- Study-guide retrieval query expansion from imported question bank.

Parsing / Assets:

- PyMuPDF for PDFs and embedded diagram extraction.
- Tesseract OCR adapter exists for OCR support.
- Extracted diagrams are stored under `data/processed/diagrams/<document_id>/` and served through safe asset routes.

Local inference:

- Ollama-backed generation adapter.
- Intended models include Phi-3 Mini, Qwen2.5 3B, DeepSeek Coder 6.7B, `nomic-embed-text`, and `bge-reranker-base`.

## Current UX Direction

The UI was moved away from a generic AI dashboard toward a custom NIRMIQ local research cockpit:

- Left rail: Source intake and source vault.
- Center: Chat-first workspace.
- Top of center: Compact pill workspace selector for Research, Chat, and Exam Lab.
- Right rail: Evidence, context, comparison, eval, and Exam Lab tooling.
- Exam Lab: Profiles, question bank import, diagram extraction, source diagram previews.
- Study guide answers render as expandable cards.

## Current Major Capabilities

Research Workspace:

- Ingest local documents.
- Query documents with hybrid/BM25/vector retrieval.
- Receive grounded answers with citations.
- Inspect citation chunks and nearby source text.
- Compare recent answer changes.
- Load retrieval evaluation reports.

General Chat:

- Chat section exists as a separate workspace.
- Offline answers are intended to use relevant local document evidence.
- If evidence is insufficient, the system should abstain instead of hallucinating.

Exam Lab:

- Save exam answer settings: marks, answer style, content type, custom instructions.
- Import question banks from pasted text.
- Store/list imported questions per document.
- Extract embedded PDF images as diagram assets.
- Store/list diagram metadata in SQLite.
- Serve diagram images safely by asset ID.
- Pack question-bank and diagram metadata into study-guide synthesis context.
- Expand retrieval queries using imported questions for study-guide and important-question modes.
- Render study-guide responses as expandable cards.
- Render diagram assets as clickable previews.

## Backend Architecture Summary

Important backend modules:

- `apps/api/app/main.py`: FastAPI app creation and router registration.
- `apps/api/app/core/config.py`: Settings.
- `apps/api/app/core/deps.py`: App container and service wiring.
- `apps/api/app/adapters/storage/sqlite_repo.py`: SQLite repository and schema initialization.
- `apps/api/app/adapters/storage/chroma_repo.py`: Chroma repository.
- `apps/api/app/adapters/retrieval/bm25_index.py`: BM25 lexical index.
- `apps/api/app/adapters/retrieval/rrf_fuser.py`: Reciprocal rank fusion.
- `apps/api/app/adapters/llm/generator.py`: Generation abstraction.
- `apps/api/app/adapters/llm/ollama_client.py`: Ollama client.
- `apps/api/app/services/ingestion_service.py`: Ingest orchestration.
- `apps/api/app/services/indexing_service.py`: Chunking/indexing orchestration.
- `apps/api/app/services/retrieval_service.py`: Retrieval flow.
- `apps/api/app/services/synthesis_service.py`: Grounded answer synthesis and fallback synthesis.
- `apps/api/app/services/query_service.py`: Query lifecycle, memory persistence, retrieval, synthesis.
- `apps/api/app/services/exam_service.py`: Exam profile, question-bank, and diagram operations.

Important API routers:

- `/health`
- `/ingest`
- `/documents`
- `/memory`
- `/query`
- `/exam`

## Frontend Architecture Summary

Important frontend files:

- `apps/web/app/page.tsx`: Main client UI and stateful app shell.
- `apps/web/app/globals.css`: NIRMIQ visual system and responsive layout.
- `apps/web/lib/api-client.ts`: Typed API client for backend calls.
- `apps/web/next.config.mjs`: Next config.

Frontend state currently handles:

- Health status.
- Ingest path/title.
- Selected document.
- Document details and visible chunks.
- Query text, history, mode, retrieval mode/profile.
- Session memory/timeline.
- Exam profile settings.
- Question-bank items.
- Diagram assets.
- Eval report input.
- Deep rail view.

## Database / Persistence Notes

SQLite tables from the MVP include:

- documents
- chunks
- ingest_jobs
- sessions
- messages
- memory_snapshots
- exam_profiles
- question_bank_items
- diagram_assets

Important V3 exam additions:

- `exam_profiles`: session/document-specific exam settings.
- `question_bank_items`: imported questions tied to documents.
- `diagram_assets`: extracted diagram file metadata tied to documents/pages.

Ignored local/generated data:

- `data/sqlite/*.db`
- `data/indexes/chroma/*`
- `temp/`
- logs and caches

## Retrieval Lifecycle

1. User submits a query from Research, Chat, or Exam Lab.
2. `QueryService` resolves retrieval mode/profile.
3. Exam modes optionally load question-bank and diagram context.
4. Study-guide and important-question modes expand retrieval query using imported questions.
5. `RetrievalService` retrieves with BM25, vector, or hybrid/RRF depending on mode.
6. Retrieved chunks are converted into citations.
7. `SynthesisService` builds a grounded prompt from retrieved chunks and optional exam context.
8. Ollama generation is attempted.
9. If generation is unavailable, fallback extractive synthesis is used.
10. Messages, citations, and retrieval metadata are persisted to SQLite when not previewing.

## Ingestion Lifecycle

1. User enters local file path and title in Source Intake.
2. `/ingest` creates/updates document record.
3. Parser extracts readable text from supported files.
4. Indexing chunks text and stores chunks in SQLite.
5. BM25 and vector stores are updated.
6. Ingest job status is persisted and displayed in UI.

Known document note:

- `C:\Downloads\daily stoic.pdf` was ingested successfully in the local environment.
- Live local state previously showed Daily Stoic with hundreds of active chunks.

## Exam Lifecycle

1. User selects Exam Lab.
2. User configures marks, answer style, content type, and custom instructions.
3. User can import a pasted question bank.
4. User can extract diagrams from source PDFs.
5. Query payload includes active exam settings.
6. Backend packs question bank and diagrams into synthesis context.
7. Study-guide mode renders generated answers as expandable guide cards.
8. Diagram assets can be clicked/opened from the right rail.

## Verification State

Latest verified commands before this context file:

- `npm run build` in `apps/web`: passed.
- Backend pytest command for unit/integration tests: passed, `6 passed`.
- API health endpoint: OK in previous verification.
- Web app at `http://127.0.0.1:3002/`: returned 200 in previous verification.
- Browser smoke test after UI refinement:
  - `Local Academic Intelligence System` visible.
  - `Source Vault` visible.
  - No bad encoding artifacts detected.
  - No Next runtime error detected.
  - No console errors detected.

## Run Instructions

Start API:

```powershell
cd C:\Nirmiq-researchOS\apps\api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start web:

```powershell
cd C:\Nirmiq-researchOS\apps\web
npm run dev
```

Open app:

```text
http://127.0.0.1:3002/
```

Run backend tests:

```powershell
cd C:\Nirmiq-researchOS
$env:PYTHONPATH='apps/api'
python -m pytest apps/api/app/tests/unit/test_health_contract.py apps/api/app/tests/integration -q
```

Run frontend build:

```powershell
cd C:\Nirmiq-researchOS\apps\web
npm run build
```

## Git / Branch State

Current working branch at time of creating this file:

- `v3-foundation`

Important branch meanings:

- `main`: V2 academic workspace baseline.
- `v3-foundation`: active V3 direction with Research, Chat, Exam Lab, exam artifacts, study-guide context, and custom UI refinement.

## Commit History

### 44aa66893ffb31f238c43122c9543f66d27cc394

Short hash: `44aa668`
Refs: `origin/main`, `main`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 10:40:06 +0530
Subject: `V2 academic workspace baseline`

Summary:

- Established the V2 baseline for the full local-first academic/research workspace.
- Added FastAPI backend, Next.js frontend, SQLite persistence, Chroma/BM25 retrieval infrastructure, ingestion, memory, query APIs, and tests.
- Added architecture, API, retrieval eval, and Codex/project documentation.
- Added local scripts for running API/web, reindexing, and retrieval evaluation.

Notable files/directories:

- `.env.example`
- `.gitignore`
- `README.md`
- `apps/api/**`
- `apps/web/**`
- `docs/**`
- `nirmiq_codex_docs/**`
- `scripts/**`
- `data/**` placeholders
- `models/.gitkeep`

Stat summary:

- 116 files changed.
- 9638 insertions.

### f6b331673bb696d2f0d606112f3b7cc4626c7437

Short hash: `f6b3316`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 10:46:12 +0530
Subject: `Start V3 workspace foundation`

Summary:

- Began V3 direction.
- Added separate workspace sections for Research, General Chat, and Exam Lab.
- Added section-aware frontend modes.
- Extended synthesis mode instructions for `general_chat`, `deep_research`, and `study_guide`.
- Added `docs/v3_foundation_plan.md` documenting the V3 direction and GraphRAG-lite preference over heavyweight graph infrastructure.

Files changed:

- `apps/api/app/services/synthesis_service.py`
- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `docs/v3_foundation_plan.md`

Stat summary:

- 4 files changed.
- 260 insertions.
- 14 deletions.

### 1b9faff3100d450a9098331ee8d8f896691f5878

Short hash: `1b9faff`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 11:04:42 +0530
Subject: `Add V3 exam lab foundation`

Summary:

- Added V3 Exam Lab backend foundation.
- Added exam schemas, router, service, and dependency wiring.
- Added SQLite tables/methods for exam profiles, question bank items, and diagram assets.
- Added frontend API client support for exam endpoints.
- Added Exam Lab UI panel for settings, question bank import, and diagram extraction/listing.
- Added integration test for profile/question-bank/diagram contracts.
- Fixed UI hit-area overlap so Exam Lab switching works reliably.

Files changed:

- `apps/api/app/adapters/storage/sqlite_repo.py`
- `apps/api/app/api/routers/exam.py`
- `apps/api/app/api/schemas/exam.py`
- `apps/api/app/core/deps.py`
- `apps/api/app/main.py`
- `apps/api/app/services/exam_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`
- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Stat summary:

- 10 files changed.
- 999 insertions.
- 5 deletions.

### 200917e621c153ea70bc6360d37b41a271e55b9d

Short hash: `200917e`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 11:09:18 +0530
Subject: `Use exam settings during grounded synthesis`

Summary:

- Added `exam_profile` to query payloads.
- Wired marks, answer style, content type, and custom instructions into synthesis prompts.
- Added retrieval metadata showing whether exam profile settings were used.
- Updated frontend query submission to include active Exam Lab settings.
- Extended integration tests to assert exam profile use during grounded query flow.

Files changed:

- `apps/api/app/api/schemas/query.py`
- `apps/api/app/services/query_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`
- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Stat summary:

- 6 files changed.
- 90 insertions.
- 4 deletions.

### 4afae1cf0149fbfe95a609eed56de57ce53435ff

Short hash: `4afae1c`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 11:25:06 +0530
Subject: `Pack exam artifacts into study guide synthesis`

Summary:

- Added lightweight Exam Context Packing in `QueryService`.
- Exam/study-guide queries now load question bank and diagram metadata from SQLite.
- Study-guide and important-question retrieval queries expand using imported question text to improve retrieval grounding.
- `SynthesisService` now includes imported questions and source diagram metadata in prompts.
- Offline fallback can produce a basic study guide from imported questions plus retrieved evidence.
- Integration tests assert exam context usage and question/diagram counts.

Files changed:

- `apps/api/app/services/query_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`

Stat summary:

- 3 files changed.
- 174 insertions.
- 6 deletions.

### 32c3c1ccbfa324be39538c223822d6262477b5c1

Short hash: `32c3c1c`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 12:34:53 +0530
Subject: `Polish study guide and diagram asset UI`

Summary:

- Added safe backend route for serving extracted diagram assets by asset ID.
- Added SQLite lookup for single diagram asset.
- Added service-level path-safety validation to prevent serving files outside processed diagram directory.
- Added frontend `diagramAssetUrl` helper.
- Rendered extracted diagrams as clickable image previews in Exam Lab.
- Rendered study-guide responses as expandable answer cards.
- Added integration check for missing diagram asset route returning 404.

Files changed:

- `apps/api/app/adapters/storage/sqlite_repo.py`
- `apps/api/app/api/routers/exam.py`
- `apps/api/app/services/exam_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`
- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Stat summary:

- 7 files changed.
- 191 insertions.
- 1 deletion.

### af6164821c89e7c972ae50200124dbef5c00290c

Short hash: `af61648`
Refs: `HEAD -> v3-foundation`, `origin/v3-foundation`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 18:02:11 +0530
Subject: `Refine NIRMIQ custom chat UI`

Summary:

- Refined the UI away from a generic AI-generated dashboard style.
- Changed visual system to a warmer custom NIRMIQ local research cockpit identity.
- Reworked the workspace selector into compact pill navigation.
- Renamed UI sections toward Source Intake and Source Vault language.
- Made the chat area visually primary.
- Removed bad encoding artifacts from visible UI text.
- Verified browser smoke state with no visible runtime error and no console errors.

Files changed:

- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`

Stat summary:

- 2 files changed.
- 191 insertions.
- 134 deletions.

## Phase Progress Summary

Phase 1: Foundational architecture

Status: Complete.

Included:

- Repository structure.
- Service boundaries.
- Ingestion lifecycle.
- Retrieval lifecycle.
- Query lifecycle.
- Memory lifecycle.
- Backend layering.
- Shared schemas.
- SQLite and Chroma foundation.
- Basic testing and API contracts.

Phase 2: Operability and workflow polish

Status: Mostly complete for MVP.

Included:

- Cleaner document browsing.
- Citation cards and citation-to-chunk drilldown.
- Query/session comparison support.
- Retrieval evaluation script and eval report UI.
- Chatbot-style UI direction started.

Phase 3 / V3 Foundation: Multi-workspace product direction

Status: In progress.

Included:

- Research workspace.
- General Chat workspace shell.
- Exam Lab workspace.
- Exam profiles.
- Question banks.
- Diagram extraction and preview.
- Study-guide generation context from question bank and diagrams.
- Custom UI refinement.

Remaining recommended V3 work:

- More ChatGPT-like center layout with optional collapsible rails.
- Dedicated General Chat API-key settings only if user explicitly wants online mode.
- Better document upload UX beyond local path input.
- More robust OCR/image extraction flow.
- Source diagram-to-chunk/page alignment.
- GraphRAG-lite concept tables and metadata expansion.
- Stronger automated retrieval evaluation datasets.
- Optional answer export for study guides.

## Design / Architecture Decisions So Far

1. Use SQLite for GraphRAG-lite first instead of TigerGraph or heavy graph infrastructure.

Reason:

- Better for local-first MVP.
- Lower operational complexity.
- Better solo-developer maintainability.
- Lower memory/VRAM footprint.

2. Keep exam features integrated into existing query flow instead of adding a new orchestration service.

Reason:

- Fewer abstractions.
- Easier to maintain.
- Keeps retrieval/synthesis path simple.

3. Prefer grounded abstention over hallucinated general answers.

Reason:

- NIRMIQ is intended to be citation-aware and source-traceable.

4. Serve diagram assets through backend by asset ID with path validation.

Reason:

- Avoid exposing arbitrary filesystem paths.
- Keeps local assets usable in the browser safely.

5. Use fallback extractive synthesis when Ollama generation is unavailable.

Reason:

- Offline/local reliability.
- Better degraded behavior than failing hard.

## Known Warnings / Notes

- Git sometimes logs: `unable to access 'C:\Users\Siddharth/.config/git/ignore': Permission denied`. This has not blocked commits or pushes.
- Next.js dev cache previously produced a stale missing chunk runtime error; clearing `apps/web/.next` and restarting web fixed it.
- The current UI is improved but can still be pushed further toward a truly ChatGPT-like interface by making side rails collapsible and keeping the composer/chat as the dominant surface.

## Suggested Next Work

1. Add collapsible left and right rails so the app can become nearly full-screen chat when desired.
2. Add a better local file picker/import workflow if feasible in the desktop environment.
3. Add General Chat online-provider settings as optional and disabled by default.
4. Add GraphRAG-lite concept extraction tables and retrieval expansion.
5. Add source diagram/page alignment and show diagrams in generated study-guide cards.
6. Add export: study guide to Markdown/PDF.
7. Build a small retrieval evaluation corpus for Daily Stoic and academic PDFs.

## Update: ChatGPT-like Shell, Paper Lab, Legal/Security, and Test Corpus

Date: 2026-05-29

This update simplified the product shell toward a ChatGPT-like workflow:

- Added a local-only login/profile gate.
- Defaulted the app to the downloaded arXiv test corpus: `Attention Is All You Need`.
- Removed Daily Stoic from the live local SQLite document store.
- Added Paper Lab as a dedicated workspace for engineering research-paper drafting with citations.
- Hid the advanced evidence/source inspector by default behind a `Sources` toggle.
- Added Privacy, Terms, and Security documents under `docs/` and `apps/web/public/`.
- Added API and web security headers.
- Added parser cleanup for common malformed PDF glyphs.
- Added better offline fallback formatting for Research Paper mode.
- Added `docs/next_version_improvements.md`.

Local test corpus status:

- Downloaded from arXiv: `https://arxiv.org/pdf/1706.03762`
- Local path: `data/raw/attention_is_all_you_need.pdf`
- Not committed to Git because it is third-party runtime/test data.
- Indexed document title: `Attention Is All You Need`
- Indexed chunks: 41
- Extracted diagrams: 3
- Imported test question-bank questions: 3

Latest verification for this update:

- `npm run build`: passed.
- Backend tests: `6 passed`.
- `python -m compileall apps/api/app`: passed.
- API health endpoint: OK.
- Web endpoint on port 3002: OK.
- Browser smoke test: login gate visible, Paper Lab visible, Daily Stoic absent, Attention paper visible after unlock, Sources drawer toggle works.

### 4ba4944

Full hash: `4ba4944` (see Git history for complete SHA)
Refs at creation: `HEAD -> v3-foundation`, `origin/v3-foundation`
Subject: `Simplify shell and add paper lab security docs`

Summary:

- Added local-only login/profile gate.
- Changed default test corpus from Daily Stoic to `Attention Is All You Need`.
- Added Paper Lab workspace and `research_paper` synthesis mode.
- Hid advanced source/evidence inspector by default behind a `Sources` toggle.
- Added API and Next.js security headers.
- Added Privacy Policy, Terms and Conditions, and Security documents in both `docs/` and `apps/web/public/`.
- Added `docs/next_version_improvements.md`.
- Added PDF text cleanup for common malformed glyph extraction.
- Improved offline fallback response structure for research paper drafting.
- Updated `.gitignore` so downloaded PDFs and extracted diagrams remain local runtime/test data.

Verification:

- `npm run build`: passed.
- Backend tests: `6 passed`.
- `python -m compileall apps/api/app`: passed.
- Local arXiv PDF indexed successfully.
- Diagram extraction produced 3 source diagrams.
- Question bank import produced 3 questions.
- Paper Lab and Study Guide API smoke tests returned grounded responses.

### Update: Chat-first Drawers and Document Purge

Date: 2026-05-30

This update moved the shell closer to ChatGPT by making chat the default single-column surface:

- Source Library is now hidden by default and opened with a `Library` button.
- Evidence/source inspector remains hidden by default and opens with `Sources`.
- The app shell now supports independent `library-open` and `inspector-open` drawer states.
- Added `DELETE /documents/{document_id}` to purge a document from SQLite document metadata, chunks, ingestion jobs, exam profiles, question-bank items, and diagram metadata.
- Added best-effort Chroma cleanup through `ChromaRepo.delete_document`.
- Added frontend `deleteDocument` client helper.
- Added `Remove selected source` control inside the Library drawer.
- Added integration test coverage for document deletion and 404 after purge.

Verification:

- `npm run build`: passed.
- Backend tests: `6 passed` with one third-party dateutil deprecation warning.
- `python -m compileall apps/api/app`: passed.
- API health endpoint: OK.
- Web endpoint on port 3002: OK.
- Browser smoke test: default chat shell visible, Library drawer opens, Remove selected source appears, Daily Stoic absent, no console errors.

### Update: Minimal NIRMIQ Academic Intelligence System UI Pass

Date: 2026-05-30

This update refined the user-facing product direction from a dashboard-like Academic Intelligence System toward a minimal, technical, ChatGPT-like workspace:

- Chose `NIRMIQ Academic Intelligence System` as the product name and retired the previous project codename for this repository.
- Added a reusable NIRMIQ brand lockup and simple placeholder `N` mark for the future logo.
- Simplified the login page headline and value proposition.
- Reworked the chat header into a compact app bar with brand, workspace switcher, and Library/Sources toggles.
- Hid session/retrieval/profile controls inside a `Tuning` disclosure in the composer.
- Shifted the visual language to a darker technical palette with phosphor green/cyan accents.
- Fixed responsive behavior so the Library is not reserved when closed and the workspace switcher remains horizontal on narrow screens.
- Updated browser metadata plus public/legal docs to use `NIRMIQ Academic Intelligence System`.

Verification:

- `npm run build`: passed.
- Local web dev server on port 3002 restarted successfully.
- Browser smoke test: `NIRMIQ Academic Intelligence System` title visible, Tuning disclosure exists, workspace switcher is horizontal, Daily Stoic absent, no console errors.

### Update: NIRMIQ Logo Selection and App Branding

Date: 2026-05-30

Logo candidates reviewed:

- `logo multiple.png`: useful reference sheet, but contains multiple variants and the older `Local-first AI Operating Ecosystem` positioning.
- `WhatsApp Image 2026-05-30 at 3.43.35 PM.jpeg`: light banner variant, readable but less aligned with the dark minimal app shell.
- `WhatsApp Image 2026-05-30 at 3.43.35 PM (1).jpeg`: dark full banner, strong but includes old positioning text and is too wide for app chrome.
- `WhatsApp Image 2026-05-30 at 3.43.35 PM (2).jpeg`: standalone dark network mark, selected as the best fit.
- `WhatsApp Image 2026-05-30 at 3.43.36 PM.jpeg`: monochrome light banner, clean but weaker for the current dark technical UI.

Decision:

- Selected the standalone dark network mark because it fits the minimal technical UI, works as an app/favicon mark, avoids conflicting old tagline text, and visually represents retrieval, memory, coordination, and research.

Implementation:

- Cropped and resized the selected candidate into `apps/web/public/brand/nirmiq-mark.png`.
- Replaced the temporary `N` placeholder mark in the login, sidebar, and app header.
- Added the mark to Next.js metadata icons.

### Update: Chat Scroll, Upload Attachments, and Performance Polish

Date: 2026-05-30

This update addressed the reported lag/confusion and missing ChatGPT-like upload workflow:

- Added `POST /ingest/upload` for direct file upload ingestion.
- Uploaded files are stored under the configured local upload path and then routed through the existing ingestion/indexing pipeline.
- Supported upload extensions: PDF, text, Markdown, PNG, JPG/JPEG, TIFF, BMP, and WebP.
- Added `UPLOAD_PATH` setting so tests and local runtime can isolate upload storage.
- Added frontend `uploadDocument` API helper.
- Added a hidden file input and visible `+` attachment button in the chat composer.
- Added an Upload file button in the Library/Source Intake drawer.
- Kept the local path ingest form as an advanced fallback.
- Fixed scroll behavior by making the chat thread a proper fixed-height scroll container.
- Reduced UI lag by removing heavy blur and entry animations.
- Slimmed the chat header by hiding the bulky title block and keeping workspace/mode controls compact.

Known note:

- Image/photo uploads are accepted. Text extraction from photos depends on local OCR availability. `Pillow` is installed, but `pytesseract` is not currently installed/configured in this environment.

Verification:

- `npm run build`: passed.
- Backend integration/unit suite: `7 passed`.
- `python -m compileall apps/api/app`: passed.
- Live API health: OK.
- Live upload smoke test: uploaded and indexed a temporary text file through `/ingest/upload`, then deleted it from the local document store.
- Browser smoke test: plus attachment button visible, upload accept types present, chat scroll container uses `overflow-y: auto`, Daily Stoic absent, no console errors.

### Update: PDF Summary Capability

Date: 2026-05-30

This update fixed the issue where broad prompts such as `Explain the pdf` could retrieve citations but still return `Please ingest documents first`.

Root cause:

- Broad document-summary prompts contain very few useful lexical terms, so retrieval scores can be low even when scoped document chunks are available.
- The synthesis safety gate previously treated low score as no usable context.

Implementation:

- Added a `summary` response mode for whole-document overviews.
- Added a Research workspace `Summarize` button in the UI.
- Expanded retrieval queries for broad summary/overview prompts with document-overview hints.
- Added document-scope fallback retrieval so selected-document summary requests can use available chunks even when lexical search has no strong hit.
- Updated synthesis grounding logic to allow low-score answers only when the user clearly asks for a document overview and at least two chunks are retrieved.
- Added fallback document-summary formatting with sections: what it is about, main ideas, useful caveats/details.
- Improved insufficient-context wording so weak partial matches do not falsely say no documents were ingested.

Verification:

- `npm run build`: passed.
- Backend integration/unit suite: `7 passed`.
- `python -m compileall apps/api/app`: passed.
- Live smoke test: `Explain the pdf` against `Attention Is All You Need` returned a grounded summary with 8 citations.
- Browser smoke test: `Summarize` mode visible, attachment button visible, Daily Stoic absent, no console errors.

### Update: Internship Impact Plan and Parsed PDF Cache

Date: 2026-05-30

This update moved the project further toward a portfolio/internship-ready academic intelligence system instead of a generic RAG chatbot.

Planning and positioning:

- Added `docs/internship_impact_plan.md`.
- Defined NIRMIQ as a local-first academic intelligence workspace for document understanding, citation-backed synthesis, engineering paper drafting, exam preparation, and retrieval evaluation.
- Added a project differentiator narrative: not just upload-and-chat, but explainable evidence, abstention, paper workflows, exam workflows, local hardware constraints, and measurable retrieval quality.
- Added a demo script, sprint roadmap, performance strategy, retrieval-quality strategy, and metrics to show in interviews.
- Updated `README.md` to point to the impact plan and reflect current V3 capabilities.

Performance optimization:

- Added parsed-PDF page caching by content hash.
- Added `PARSE_CACHE_PATH` setting with default `data/cache/parsed_pages`.
- Wired `PyMuPDFParser(cache_root=...)` through the app container.
- The cache stores cleaned page text as local JSON and safely falls back to normal parsing if cache read/write fails.
- Added isolated test cache path for test runs.
- Added unit test coverage proving the parser reuses the cache for repeated parses of the same PDF content.

Why it matters:

- Faster repeated reindexing during demos, evaluation, and local experimentation.
- Better RTX 4050/local-laptop experience because less time is wasted reparsing unchanged PDFs.
- Stronger engineering story: measurable local performance improvement without adding infrastructure.

Verification:

- Backend unit/integration suite: `8 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

### Update: Source Cockpit and One-Click Summary UI

Date: 2026-05-30

This update improved the live app UI for usefulness and demo clarity:

- Added a compact source cockpit above the composer.
- Shows the selected source name directly where the user asks questions.
- Shows selected-source chunk count.
- Shows current grounding state near the composer instead of hiding it in the source drawer.
- Added one-click `Summarize PDF` action wired to the grounded `summary` mode.
- Added a secondary `Upload` quick action beside the source cockpit.
- Replaced noisy grounding chips with a calmer composer hint.
- Updated the empty state to guide the user toward the intended workflow: upload source, summarize first, then ask deeper questions.
- Ensured summary action does not accidentally inherit Exam Lab formatting.

Why it matters:

- Makes the app less confusing because source selection is visible at the point of asking.
- Makes the project demo stronger: upload/select PDF -> click Summarize PDF -> inspect citations.
- Supports the internship-positioning story by making grounded document intelligence obvious without opening debug panels.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.

### Update: Compact Research Composer and Logo Alignment

Date: 2026-05-30

This update fixed the issue where the query/composer box consumed too much vertical space and made research responses hard to read.

Changes:

- Reduced composer padding and card height.
- Made the source cockpit a compact single-line command strip.
- Reduced textarea height for research-style querying.
- Moved the primary `Ask` button into the input row.
- Converted `Clear Thread` into a compact text action.
- Hid the composer hint by default to prioritize response visibility.
- Tightened top header spacing.
- Adjusted NIRMIQ logo sizing and lockup alignment in the app header.

Measured result in browser:

- Composer height reduced from approximately `279px` to approximately `173px`.
- Response scroll area increased from approximately `292px` to approximately `397px` on the tested viewport.
- Source cockpit reduced to approximately `38px` height.
- Logo lockup is centered with a `42px` mark height.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.
- Live browser smoke test: compact composer visible, `Ask` button in input row, scroll remains enabled, logo aligned, no console errors.

### Update: V3 Landing, Login, Minimized Composer, Exam PDF Action, and Handoff Docs

Date: 2026-05-30

This update continued the V3 direction: make NIRMIQ feel closer to ChatGPT in daily use while preserving its academic intelligence identity.

Product/UX changes:

- Reworked the local entry screen into a stronger NIRMIQ Academic Intelligence System landing page.
- Added a compact animated hero/orbit visual to make the first screen feel intentional without adding heavy dependencies.
- Added local profile fields for name, email, and phone.
- Kept login local-only for now; this is a profile/personalization gate, not real hosted authentication yet.
- Clarified the four workspaces: Research, Chat, Paper Lab, and Exam Lab.
- Made composer placeholder text and primary action labels change by workspace.
- Added a `Minimize` / `Open Search` control so long answers can be read more comfortably.
- Added an Exam Lab `Custom PDF` action that opens the current grounded answer in a printable document view.
- Kept citations available through grounded badges, evidence chips, and the Sources drawer instead of forcing every panel onscreen.

Architecture/documentation changes:

- Added `prd.md` for product requirements and V3/V4 direction.
- Added `trd.md` for technical requirements and acceptance criteria.
- Added `UI_UX.md` for the UI/UX specification. The requested `UI/UX.md` filename was normalized because Windows treats `/` as a path separator.
- Added `backend_architecture.md` for service boundaries, data lifecycles, and next backend upgrades.
- Added `debugging.md` for run commands, test commands, and common issue fixes.
- Added `codex_implementaton.md` as requested to preserve Codex implementation history and future workflow notes.

Research references used for V3 planning:

- OWASP Authentication Cheat Sheet for future real auth/security posture.
- W3C WCAG 2.2 for visible focus and usable target-size guidance.
- NIST AI Risk Management Framework for trust, grounding, and risk framing.

Why it matters:

- The app now starts with a clearer product story instead of opening directly into a complex workspace.
- The composer no longer has to occupy reading space permanently.
- Each section can now feel purpose-built while sharing one maintainable query flow.
- Future Codex sessions can use the new docs as the source of truth instead of replaying the entire chat.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.

### Latest Update: V3.1 Performance-Safe Motion Polish

Date: 2026-05-30

This is the latest completed work unit. A lightweight CSS-first motion system was added to make NIRMIQ feel smoother and more futuristic without adding new dependencies or heavy processor/GPU effects.

Latest changes:

- Added motion tokens, soft page boot, landing reveal, workspace underline scan, drawer slide-in, composer dock/minimized pill animation, assistant answer reveal, citation chip stagger, and one-time source-ready pulse.
- Added visible focus states and `prefers-reduced-motion` safeguards.
- Updated `UI_UX.md` with the motion direction and performance constraints.
- Restarted the Next dev server after a stale hot-reload cache error; no `.next` deletion was required.

Latest verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.
- Live browser smoke test: page loads on `http://127.0.0.1:3002`, motion tokens are active, app boot/composer animations are active, source cockpit remains compact, `Minimize` is visible, and console has no errors.

### Latest Update: NIRMIQ Academic Intelligence System Brand Migration

Date: 2026-05-30

This update migrated the repository identity away from the previous project name and toward **NIRMIQ Academic Intelligence System** as the standalone academic product under the broader NIRMIQ ecosystem.

Changes:

- Created a custom vector logo at `apps/web/public/brand/nirmiq-ais-mark.svg`.
- Updated the Next.js app metadata, favicon path, visible UI tagline, API title, backend package description, and web package name.
- Updated README, PRD, TRD, UI/UX, legal docs, architecture docs, Codex docs, and context docs to use the new product name.
- Added `docs/nirmiq_ecosystem.md` to explain NIRMIQ OS, Mirror, Intelligence Engine, Agent System, Academic Intelligence System, and Echo.
- Preserved actual local paths such as `C:\Nirmiq-researchOS` so the current workspace keeps running.
- Recorded the target GitHub repository slug: `NirmiqAcademicIntelligenceSystem`.

Notes:

- GitHub CLI is not installed in the current environment, so the remote repository could not be renamed from the terminal during this update.
- The current git remote should remain usable until the GitHub repository is renamed manually or via GitHub CLI.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.
- Local web server restarted successfully on `http://127.0.0.1:3002`.
- Browser smoke test: page title is `NIRMIQ Academic Intelligence System`, visible tagline is `ACADEMIC INTELLIGENCE SYSTEM`, visible logo uses `/brand/nirmiq-ais-mark.svg`, no visible ResearchOS branding in the app shell, and console has no errors.

### Latest Update: Accuracy and Remote Codex Audit

Date: 2026-05-31

This update started a reliability sprint focused on retrieval precision, hallucination resistance, and remote Codex readiness.

Research basis:

- RAGAS for context relevance, faithfulness, and answer-quality evaluation dimensions.
- ARES for automated RAG evaluation around context relevance, answer faithfulness, and answer relevance.
- Self-RAG and chain-of-verification patterns for retrieve/generate/critique and claim verification.
- Official OpenAI Codex docs for local CLI, Codex web/GitHub, mobile/remote continuity, and workspace controls.

Implemented:

- Added deterministic cited-claim verification in `SynthesisService`.
- Unsupported cited claims now trigger a safe extractive fallback rewrite instead of allowing unsupported fluent output through.
- Added retrieval metadata for `citation_verification_state`, checked claim count, unsupported claims, original unsupported claims, and rewrite status.
- Added UI answer-card badges for citation verification and faithfulness rewrites.
- Added unit tests for supported and unsupported cited generations.
- Added `docs/accuracy_precision_audit.md`.
- Added `docs/remote_codex_access.md`.

Known limitation:

- The current verifier is lexical and local-first. It is intentionally cheap and deterministic, but not a full semantic entailment model.

Verification:

- Backend unit/integration suite: `10 passed`.
- `npm run build`: passed.
- `python -m compileall apps/api/app`: passed.
- Local web server restarted successfully on `http://127.0.0.1:3002`.
- Browser smoke test: NIRMIQ Academic Intelligence System UI loads, workspace tabs are visible, no old ResearchOS branding appears in the app shell, and console has no errors.

### Latest Update: Chunk Quality Scoring and Portable GitHub CLI

Date: 2026-05-31

This update improved retrieval precision without adding new UI complexity.

Changes:

- Added chunk quality scoring during indexing.
- Stored `quality_score` on `document_chunks`.
- Added SQLite migration logic for existing local databases.
- Passed quality score into Chroma metadata when vector storage is available.
- Applied quality weighting during retrieval scoring so noisy PDF/OCR chunks are less likely to dominate context.
- Added retrieval metadata for average chunk quality and quality weighting.
- Added unit tests for clean academic text and noisy PDF text.
- Added `tools/gh/` to `.gitignore`.
- Installed portable GitHub CLI at `C:\Nirmiq-researchOS\tools\gh\bin\gh.exe` because Winget/MSI system install was blocked by a stuck Windows Installer process.

User impact:

- The app stays simple. No new control is shown.
- Retrieval should quietly prefer readable, useful chunks over malformed PDF extraction garbage.
- GitHub CLI is available locally, but GitHub auth still needs user login.

Verification:

- Backend unit/integration suite: `12 passed`.
- `npm run build`: passed.
- `python -m compileall apps/api/app`: passed.
- Portable GitHub CLI version check passed: `gh version 2.92.0`.
- `gh auth status` confirms authentication is still pending.

### Latest Update: V3 Security, Privacy, and Adaptive Generation Hardening

Date: 2026-06-02

This update tightened the project without adding interface complexity.

Implemented:

- Restricted direct local-path ingestion to configured trusted corpus roots.
- Added `LOCAL_INGEST_ALLOWED_ROOTS` and `SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS=false`.
- Preserved normal app uploads by storing uploaded files inside the project raw-data area.
- Added lightweight content validation for PDF, image, text, and Markdown uploads to reduce extension-spoofing risk.
- Added adaptive generation temperature:
  - Grounded factual/summary/exam paths stay conservative by default.
  - Long-context deep research, paper drafting, and study-guide synthesis can use `0.85` when enough evidence is retrieved.
  - Citation-faithfulness verification still runs after generation.
- Added backend unit tests for ingestion privacy and upload validation.
- Added a local agent plan that keeps future agent behavior local, tool-limited, and approval-aware rather than unbounded.

Tradeoffs:

- Direct local-path ingestion is safer but now requires files to be under allowed roots unless explicitly overridden.
- Higher-temperature generation is not global, because summary/exam/factual answers need reliability more than stylistic variety.
- The local agent was documented rather than fully implemented to avoid complicating V3 before Version 4 requirements arrive.

Verification:

- Backend unit/integration suite: `17 passed`.
- `npm run build`: passed.
- `python -m compileall apps/api/app`: passed.

### Latest Update: V3.1 Faster Summaries, Intent Routing, and Trust Signals

Date: 2026-06-06

This update implemented the planned V3.1 reliability/performance increment without adding new user-facing complexity.

Implemented:

- Added SQLite-backed `document_summaries` cache for selected-document summary mode.
- Cache key uses document id, content hash, and summary profile, so source edits/reindexing naturally miss stale summaries.
- Document deletion now purges cached summaries.
- Added deterministic query intent routing for summary, factual lookup, compare, deep research, paper draft, exam, general chat, and unclear prompts.
- Added retrieval metadata for `cache_hit`, `detected_intent`, `intent_confidence`, and `intent_route`.
- Added citation coverage metadata: `citation_coverage`, `citation_sentence_count`, and `citation_anchor_count`.
- Updated the UI trust chip to show one compact label: `Verified`, `Rewritten`, `Needs review`, or `Low citation coverage`.
- Added unit tests for intent routing, citation coverage, and summary cache storage.
- Expanded integration coverage for summary cache miss, cache hit, stale-content miss after reindex, and cache purge on document delete.

Tradeoffs:

- Intent routing is deterministic and lexical to stay fast/offline; it should be tuned with a labeled evaluation dataset next.
- Summary cache is limited to selected-document summary requests, avoiding ambiguous corpus-wide cache behavior.
- Citation coverage checks anchor presence, while citation-faithfulness verification remains responsible for claim support.

Verification:

- Backend unit/integration suite: `25 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.
- Browser plugin was unavailable in this session, so browser smoke was not run.

Commit:

- Pending until the implementation commit is created.
