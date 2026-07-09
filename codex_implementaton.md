# Codex Implementation Log

Last updated: 2026-07-09

Note: filename spelling follows the user request: `codex_implementaton.md`.

## Standing Project Rule

After each meaningful project work unit:

- Update `context.md`.
- Commit changes.
- Push to GitHub.

## Current Branch

- `main`

## 2026-07-09 MegaSprint One Implementation Note

- Implemented query-agnostic RAG reliability improvements instead of mandatory prompt-specific regression cases.
- Added document-aware query expansion, direct-evidence retrieval scoring, stronger backmatter penalties, and synthesis relevance states.
- Simplified UI trust labels to `Verified`, `Needs more evidence`, and `Not found in sources`.
- Hid raw metadata from the normal chat/source flow.
- Added `data/processed/eval/query_agnostic_rag_categories.jsonl`.
- Backend verification after implementation: `71 passed`, `1` warning.

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

### V4 Golden Demo Sprint

- Commit: `928906b` (`Add golden demo sprint`).
- Installed `llm-council` and `graphify` Codex skills for future planning/graph workflows.
- Ran a council-style sprint review and selected the golden demo strategy.
- Added bundled local demo corpus under `data/raw/golden_demo`.
- Added `scripts/golden_demo.ps1` to warm-start the corpus and run citation-bearing smoke queries.
- Added one-click `Load Golden Demo` UI flow.
- Added locked demo prompts for Research, Summary, Paper Lab, Exam Lab, and abstention.
- Added compact Deep Research proof strip using existing retrieval metadata.
- Added local Markdown export for answer plus citations.
- Added `docs/demo_script.md` and `docs/benchmark_report.md`.
- Added General Chat context-relevance gating so unrelated retrieved chunks cannot produce a grounded answer.
- Hardened `scripts/golden_demo.ps1` to fail if the abstention prompt returns grounded output or citations.
- Verified the sprint with backend tests, API compile, frontend production build, and golden demo smoke.

### V4 EOD Launch Sprint

- Resolved the Folio reference to `kartikdubey17/FOLIO` release `v0.1.0`.
- Added `docs/folio_competitive_review.md` to define the competitive response.
- Added `scripts/run_local.ps1` for one-command local preview.
- Added `scripts/stop_local.ps1` for scoped launcher cleanup.
- Added `NIRMIQ ResearchOS.cmd`, `NIRMIQ Stop.cmd`, and `scripts/create_windows_shortcut.ps1` for Windows app-like launch.
- Added `docs/windows_app_packaging.md`.
- Added `scripts/ship_check.ps1` for full EOD verification.
- Hardened `scripts/publish_smoke.ps1` with more realistic local readiness timeouts.
- Hardened `scripts/stop_local.ps1` to terminate the full Next.js child process tree and avoid stale `.next` cache errors.
- Updated README, publish checklist, and project context with the one-command run path.
- Updated the landing screen proof chips to emphasize offline core, citation trail, abstention, and Paper/Exam labs.
- Verified `scripts/ship_check.ps1` end to end on 2026-06-11 and recreated a persistent preview afterward.

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
- Use `scripts/run_local.ps1 -GoldenDemo -OpenBrowser` for reviewer preview.
- Use `scripts/ship_check.ps1` as the strongest pre-publish verification.
- Use `scripts/golden_demo.ps1` to verify the reviewer proof path and abstention behavior before recording demos.
- Treat FastAPI as the local backend runtime, not a cloud API dependency.
- Keep ChatGPT/OpenAI account usage as a future optional add-on only.

## Current Verification Routine

- `npm run build` from `apps/web`.
- Backend unit/integration tests from repo root with `PYTHONPATH=apps/api`.
- `scripts/golden_demo.ps1` after the backend is running.
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

## Latest Minimal ChatGPT-Style UI Transformation

Date: 2026-06-09

- Made Chat the default primary workspace while preserving Research, Paper Lab, and Exam Lab.
- Reworked the left rail into a ChatGPT-like study sidebar with New Study Thread, recent study threads, Study Material upload, Knowledge Base, and local runtime status.
- Kept upload in the composer and moved local-path ingestion behind an advanced disclosure.
- Replaced the user-facing `Sources` toggle with a collapsible `Deep Research` panel.
- Added answer-level trust copy, Evidence Trail labeling, and a `View Deep Research` action under assistant responses.
- Moved detailed mode routing into compact composer tuning with a `Route` selector.
- Simplified the local landing/login screen and cleaned safe ResearchOS naming traces.
- Cleaned public privacy, terms, and security markdown naming traces.
- Retuned visible UI colors toward graphite, research ivory, oxide copper, deep teal, and sage.

Verification:

- `npm run build`: passed.
- Active frontend/legal naming scan: passed.
- Browser visual QA unavailable because no callable browser inspection tool was exposed in this session.

Remaining UI debt:

- Split `apps/web/app/page.tsx` into smaller components.
- Manually review mobile sidebar and Deep Research panel behavior.
- Reduce density inside Deep Research after real usage feedback.
- Commit: `d19de62` - Transform UI into ChatGPT-style study shell.

## 2026-06-11 Implementation Log - Accuracy Rescue

Work completed:

- Diagnosed the answer-quality failure against a real indexed textbook.
- Found missing default model, Qwen empty-response behavior, short Ollama timeout, stale document rows, weak overview retrieval, and loose faithfulness checks.
- Implemented installed-model routing and Mistral-first answer generation for the current machine.
- Added summary/factual context seeding, lightweight retrieval stemming, citation anchoring, and conservative unsupported-claim rewrite.
- Added tests for the new reliability path.
- Reindexed the selected textbook and validated live API answers.

Files touched in this implementation:

- `apps/api/app/adapters/llm/generator.py`
- `apps/api/app/adapters/llm/ollama_client.py`
- `apps/api/app/adapters/llm/reranker.py`
- `apps/api/app/adapters/retrieval/bm25_index.py`
- `apps/api/app/core/config.py`
- `apps/api/app/services/documents_service.py`
- `apps/api/app/services/query_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/unit/test_bm25_stemming.py`
- `apps/api/app/tests/unit/test_low_memory_runtime.py`
- `apps/api/app/tests/unit/test_synthesis_faithfulness.py`

Verification:

- Backend tests: `34 passed, 1 warning`.
- Compileall: passed.
- Web build: passed.

## 2026-06-19 Implementation Log - Windows Desktop Shell

Work completed:

- Added a lightweight Electron desktop wrapper under `apps/desktop`.
- Preserved the existing FastAPI + Next.js architecture and avoided duplicating product logic.
- Added desktop launch, install, pack, and portable packaging commands.
- Added menu-based developer affordances for runtime status, restart, logs, VS Code, project docs, and local data access.
- Added a secure preload bridge with no broad Node exposure.
- Added Windows `.cmd` launcher and shortcut support.
- Documented desktop usage, packaging, and debugging flows.

Validation:

- Desktop JS syntax checks passed.
- Electron production dependency audit passed with 0 vulnerabilities.
- Unpacked Windows app packaging passed.
- Portable Windows EXE packaging passed after redirecting Electron Builder cache to the workspace.
- Backend tests passed: 37 passed, 1 warning.
- API compile passed.
- Web production build passed.

Files introduced:

- `apps/desktop/package.json`
- `apps/desktop/package-lock.json`
- `apps/desktop/src/main.js`
- `apps/desktop/src/preload.js`
- `apps/desktop/README.md`
- `NIRMIQ Desktop.cmd`
- `scripts/start_desktop.ps1`
- `scripts/package_desktop.ps1`

Files updated:

- `package.json`
- `.gitignore`
- `README.md`
- `debugging.md`
- `backend_architecture.md`
- `trd.md`
- `docs/windows_app_packaging.md`
- `scripts/create_windows_shortcut.ps1`
- `context.md`
- `codex_implementaton.md`

Commit:

- `ca2a83c` - Add Windows desktop shell.

Follow-up correction after packaging validation:

- Added robust desktop project-root detection for packaged Electron runs.
- Documented `NIRMIQ_ROOT` fallback for unpacked/portable builds.
- Revalidated desktop syntax, unpacked packaging, portable packaging, and web build.

## 2026-06-19 Implementation Log - Desktop Startup Fix

Work completed:

- Reproduced the desktop startup failure.
- Found Electron/Chromium GPU process crash as the primary blocker.
- Found Windows `Path`/`PATH` child-process environment duplication as a secondary reliability risk.
- Added GPU-safe Electron launch flags.
- Added workspace-local Electron user data path.
- Sanitized spawned child process environments.
- Routed spawned Windows commands through `cmd.exe` for stable npm/python resolution.
- Added early spawn/exit logging and Next production-to-dev fallback.
- Updated desktop/debugging docs.

Validation:

- Live desktop startup probe returned HTTP 200 for both API and web while the desktop app was running.
- Desktop syntax checks passed.
- Desktop production dependency audit passed.
- Desktop unpacked and portable packaging passed.
- Backend tests passed: 37 passed, 1 warning.
- API compile passed.
- Web build passed.

Commit:

- `690196c` - Fix Windows desktop startup.

## 2026-06-20 Implementation Log - Fault Audit And Ship Hardening

Work completed:

- Used the multi-agent review output to prioritize correctness faults over cosmetic changes.
- Hardened ingestion, indexing, retrieval scoring, faithfulness checks, frontend query behavior, desktop cleanup, Docker exposure, and release scripts.
- Kept the implementation low-complexity and local-first; no graph database, cloud provider, or local agent was added in this sprint.

Backend files changed:

- `apps/api/app/core/deps.py`
- `apps/api/app/services/indexing_service.py`
- `apps/api/app/services/ingestion_service.py`
- `apps/api/app/services/query_service.py`
- `apps/api/app/services/retrieval_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/integration/test_ingest_query_flow.py`
- `apps/api/app/tests/unit/test_synthesis_faithfulness.py`

Frontend files changed:

- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Runtime/release files changed:

- `apps/desktop/src/main.js`
- `NIRMIQ ResearchOS.cmd`
- `NIRMIQ Golden Demo.cmd`
- `docker-compose.local.yml`
- `scripts/bootstrap.ps1`
- `scripts/create_windows_shortcut.ps1`
- `scripts/package_desktop.ps1`
- `scripts/run_local.ps1`
- `scripts/run_web.ps1`
- `scripts/ship_check.ps1`
- `scripts/start_desktop.ps1`
- `scripts/stop_local.ps1`

Docs updated:

- `README.md`
- `backend_architecture.md`
- `trd.md`
- `debugging.md`
- `docs/accuracy_precision_audit.md`
- `docs/publish_checklist.md`
- `docs/security.md`
- `docs/windows_app_packaging.md`
- `context.md`
- `codex_implementaton.md`

Validation:

- `npm.cmd run test:api`: `41 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.
- `npm.cmd run desktop:pack`: passed.
- `docker compose -f docker-compose.local.yml config`: passed with non-blocking user Docker config warning.
- `node --check apps\desktop\src\main.js`: passed.
- `node --check apps\desktop\src\preload.js`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ship_check.ps1`: passed.

Known remaining debt:

- `apps/web/app/page.tsx` still needs a component split.
- UI success/error messaging still shares the same state in several paths.
- Full local purge does not yet delete parse cache, extracted diagrams, or app-owned uploaded raw copies.
- Real-world retrieval labels and screenshot/GIF demo assets are still needed before a polished public launch.

Commit:

- `5e21194` - Harden retrieval and ship checks.

## 2026-06-20 Implementation Log - Polish Sprint

Work completed:

- Reduced frontend monolith risk by extracting shared page model/helpers and two client components.
- Added a real-world phrase-level retrieval seed benchmark using local academic PDFs/notes without committing copyrighted source files.
- Extended purge behavior to remove app-owned uploaded source copies, parse-cache files, and extracted diagram directories.
- Added README visual polish through a committed SVG demo flow and updated demo asset guidance.
- Added Linux/low-end browser-preview scripts and feasibility documentation.

Files introduced:

- `apps/web/app/page-model.ts`
- `apps/web/components/local-login.tsx`
- `apps/web/components/study-guide-answer.tsx`
- `data/processed/eval/real_world_academic_seed.jsonl`
- `data/processed/eval/real_world_retrieval_metrics.json`
- `docs/assets/nirmiq-demo-flow.svg`
- `docs/linux_low_end_feasibility.md`
- `scripts/eval_real_world.ps1`
- `scripts/start_local.sh`
- `scripts/stop_local.sh`

Key behavior changes:

- `scripts/eval_retrieval.py` supports `source_file` labels and `--auto-ingest-sources`.
- `DocumentsService.purge_documents` deletes app-owned uploads, parse cache, and diagrams while preserving arbitrary external local-path source files.
- Purge response includes source/derived deletion counts.
- Root `package.json` includes `start:linux` and `stop:linux`.

Validation:

- `npm.cmd run build`: passed.
- `npm.cmd run test:api`: `41 passed, 1 warning`.
- `python -m compileall scripts apps/api/app`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_real_world.ps1`: passed.
- Bash validation could not run because WSL has no installed Linux distribution.

Remaining debt:

- More frontend components should be extracted.
- Real-world eval needs 60+ labels and failure analysis.
- Live UI screenshots/GIFs still need capture.
- Linux scripts need validation on a real Linux distro.

Commit:

- `a980cdc` - Polish UI structure eval purge and Linux docs.

### Windows App Package Refresh And Shortcuts

Date: 2026-06-20

Implementation:

- Rebuilt the web app with `npm.cmd run build`.
- Repacked the Electron desktop target with `npm.cmd run desktop:pack`.
- Rebuilt the portable desktop package with `npm.cmd run desktop:package`.
- Refreshed `dist/desktop/NIRMIQ ResearchOS 0.1.0.exe` and `dist/desktop/win-unpacked/NIRMIQ ResearchOS.exe`.
- Ran `scripts/create_windows_shortcut.ps1 -Desktop -StartMenu` to create Desktop and Start Menu shortcuts.

Validation:

- Web build passed.
- Desktop pack passed.
- Portable desktop package passed.

Tradeoff:

- The current package target is Windows desktop. Android APK support is intentionally not added yet because it needs separate mobile packaging decisions and would distract from the local-first Windows demo path.
