# NIRMIQ ResearchOS Context

Last updated: 2026-05-29
Current branch: `v3-foundation`
Repository: `https://github.com/SheeshDarth/NirmiqResearchOS`
Local workspace: `C:\Nirmiq-researchOS`
Primary app URL: `http://127.0.0.1:3002/`
API URL: `http://127.0.0.1:8000/`

## Project Metadata

Project name: NIRMIQ ResearchOS
Project type: Offline-first adaptive AI research operating system
Owner/developer: Siddharth / SheeshDarth
Target user: Solo local-first researcher/student/developer
Target machine: RTX 4050 laptop class hardware
Primary branch for current work: `v3-foundation`
Stable baseline branch: `main`

## Product Direction

NIRMIQ ResearchOS is a local-first document intelligence workspace for:

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
  - `Local Research OS` visible.
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

### Update: Minimal NIRMIQ Academic Intelligence UI Pass

Date: 2026-05-30

This update refined the user-facing product direction from a dashboard-like research OS toward a minimal, technical, ChatGPT-like workspace:

- Chose `NIRMIQ Academic Intelligence` as the user-facing name while keeping ResearchOS as the project/system codename.
- Added a reusable NIRMIQ brand lockup and simple placeholder `N` mark for the future logo.
- Simplified the login page headline and value proposition.
- Reworked the chat header into a compact app bar with brand, workspace switcher, and Library/Sources toggles.
- Hid session/retrieval/profile controls inside a `Tuning` disclosure in the composer.
- Shifted the visual language to a darker technical palette with phosphor green/cyan accents.
- Fixed responsive behavior so the Library is not reserved when closed and the workspace switcher remains horizontal on narrow screens.
- Updated browser metadata plus public/legal docs to use `NIRMIQ Academic Intelligence`.

Verification:

- `npm run build`: passed.
- Local web dev server on port 3002 restarted successfully.
- Browser smoke test: `NIRMIQ Academic Intelligence` title visible, Tuning disclosure exists, workspace switcher is horizontal, Daily Stoic absent, no console errors.

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
