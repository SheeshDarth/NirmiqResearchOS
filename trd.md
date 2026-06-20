# NIRMIQ Technical Requirements Document

Last updated: 2026-06-20

## Project

NIRMIQ ResearchOS is an offline-first academic workspace for grounded document research, general chat, paper drafting, and exam preparation. The implementation target is a solo-developer MVP that runs well on a local laptop with RTX 4050-class constraints.

It belongs to the broader NIRMIQ ecosystem, but this repository must remain independently runnable and useful without NIRMIQ OS, Mirror, Intelligence Engine, Agent System, or Echo.

## Runtime Requirements

- Frontend: Next.js PWA at `apps/web`.
- Backend: FastAPI at `apps/api`.
- Desktop shell: Electron app at `apps/desktop` for Windows local review, runtime diagnostics, and app-style launch.
- Storage: SQLite for metadata, memory, sessions, exam artifacts, and document chunks.
- Vector storage: ChromaDB optional path for semantic retrieval.
- Retrieval: BM25, optional vector retrieval, Reciprocal Rank Fusion, reranking hooks, citation packing.
- Parsing: PyMuPDF for PDFs, Tesseract OCR as optional fallback for low-text/scanned pages and images.
- Local inference: Ollama generation and embeddings when available, deterministic/fallback paths when unavailable.
- Connected ChatGPT/OpenAI account usage is optional future enhancement only, not required for core operation.
- Hardware priority: low VRAM, graceful fallback, fast local demos.

## Functional Requirements

- Upload PDFs, text, Markdown, and images through a ChatGPT-like composer.
- Launch through either browser preview or the Electron desktop shell without changing API behavior.
- Load a bundled golden demo corpus from trusted local raw files.
- Ingest uploaded or local-path documents into raw storage, parsed pages, chunks, indexes, and document metadata.
- Ask grounded questions against selected documents.
- Summarize a whole PDF even when the prompt is broad.
- Show citations only when useful, with source page/chunk detail.
- Support four workspace modes: Research, Chat, Paper Lab, Exam Lab.
- Provide a local login/profile gate using name plus email or phone.
- Let users minimize the composer/search box to read long responses.
- Let Exam Lab generate printable custom PDF study material from grounded answers.
- Keep session continuity through SQLite-backed message history and memory snapshots.
- Restrict direct local-path ingestion to configured corpus roots by default.
- Validate uploaded file signatures/readability before indexing.
- Apply the same suffix, size, and lightweight signature/readability checks to direct local-path ingestion.
- Preserve existing active chunks when a reindex attempt extracts no readable text.
- Use adaptive generation temperature with conservative grounded defaults and higher long-context drafting settings.
- Use bounded local model runtime settings for Ollama context, generation length, keep-alive, optional GPU/thread controls, and embedding batches.
- Cache selected-document summaries by document id, content hash, and summary profile.
- Add deterministic query intent metadata without changing the public query request shape.
- Compute citation coverage metadata for generated and fallback answers.
- Add Paper Lab metadata for paper-draft responses: outline, citation clusters, and related-work matrix.
- Provide client-side Markdown export for grounded Paper Lab drafts.

## Non-Functional Requirements

- Offline-first: core document Q&A should work without internet.
- Local-first: the local FastAPI backend is part of the app runtime, not a cloud API dependency.
- Privacy-first: documents remain local by default.
- Maintainable: prefer fewer services and explicit orchestration.
- Stable: backend tests must isolate temp SQLite/Chroma/cache paths.
- Grounded: response generation must cite retrieved chunks or abstain when context is weak.
- Relevant: General Chat must abstain when retrieved chunks do not overlap the actual subject of the user query.
- Faithful: cited generated claims must pass deterministic verification or be rewritten to extractive fallback.
- Active-source safe: retrieved vector hits must be ignored when the chunk is no longer active in SQLite.
- Honest scoring: summary/factual seed chunks may expand context but must not inflate grounding confidence.
- Fast enough for demos: repeated PDF parsing should use content-hash page cache.
- Efficient: repeated selected-document summaries should reuse SQLite cache until source content changes.
- Memory efficient: default runtime profile should remain stable on RTX 4050-class hardware without requiring cloud APIs.

## API Requirements

- `GET /health`: service health and dependency status.
- `GET /api/v1/health`: versioned alias for health.
- `GET /health/readiness`: local demo readiness, indexed document count, active chunk count, vector/Ollama availability, and local-first status.
- `POST /ingest`: ingest document by source path.
- `POST /ingest/upload`: upload file and ingest it.
- `GET /ingest/{document_id}`: document status and latest job.
- `GET /ingest/{document_id}/jobs`: ingestion job history.
- `GET /documents`: indexed document library.
- `GET /documents/{document_id}/chunks`: source drilldown.
- `POST /query`: grounded query flow with retrieval mode/profile/mode/session.
- `POST /query` debug metadata may include cache hit, detected intent, intent route, and citation coverage fields.
- `POST /query` debug metadata may include `paper_lab` only for paper-draft intent.
- `GET /memory/{session_id}`: session memory snapshot.
- `GET /memory/{session_id}/export`: local Markdown export of the session.
- `DELETE /memory/{session_id}`: clear local session messages and snapshots.
- `DELETE /documents`: clear all indexed material, metadata, summaries, jobs, exam artifacts, and vector entries without deleting source files from disk.
- Exam routes for profiles, question banks, and study/exam artifacts.
- `/api/v1/*` aliases must remain available for all current API groups while legacy local routes remain stable for the existing frontend.

## Retrieval Requirements

- Use hybrid retrieval by default.
- Support `bm25`, `vector`, and `hybrid` modes.
- Use retrieval profiles: `fast`, `balanced`, `precision`.
- Route broad overview prompts to summary behavior.
- Use document-scoped fallback when a selected document exists and broad prompts retrieve low lexical scores.
- Include debug metadata for evaluation and development.
- Use deterministic intent routing to expand retrieval hints for summaries, comparisons, deep research, paper drafting, and exam workflows.
- Apply a lightweight query/context relevance gate before General Chat synthesis so old corpus chunks do not create false grounded answers.
- Apply Exam Lab relevance against imported question-bank text for study-guide/important-question flows.
- Paper drafting responses should expose deterministic paper-structure metadata without adding another generation pass.
- Avoid graph databases in V3 unless the measured baseline proves SQLite concept graph expansion is insufficient.

## Security And Privacy Requirements

- Local profile login is not real authentication yet; it is a UX gate and personalization layer.
- Future hosted auth must follow OWASP guidance: generic errors, safe session handling, rate limits, and secure reset/verification flows.
- Uploaded documents must stay local unless the user explicitly enables an external provider.
- Direct local-path ingestion must stay restricted by `LOCAL_INGEST_ALLOWED_ROOTS` unless `SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS=true`.
- File uploads must be content-checked for common spoofing cases before indexing.
- Any future API-key mode must make cloud usage obvious before sending content.
- Provide local data purge/export controls before broader beta use.
- Provide a scoped golden demo warm-start script that indexes bundled files and checks citation-bearing smoke queries.
- Enforce a configurable request body size limit through `MAX_REQUEST_BODY_BYTES`.
- Keep HSTS and CSP opt-in for production/proxy deployments, not enabled by default for local HTTP.
- Avoid cloud error tracking by default; prefer local bug-report bundle export for the offline/privacy posture.
- Keep checked-in Dockerfiles and CI config current enough for reviewer verification.

## V3 Acceptance Criteria

- Landing screen explains NIRMIQ ResearchOS clearly.
- Login accepts display name plus email or phone.
- Workspace section choice is clear: Research, Chat, Paper Lab, Exam Lab.
- Composer adapts placeholder/action to the current section.
- Composer can be minimized and restored.
- Research summary works on an indexed PDF.
- Exam Lab exposes custom PDF generation from the current grounded answer.
- Web build passes.
- Backend unit/integration tests pass.
- Desktop unpacked packaging passes.
- Full `scripts/ship_check.ps1` passes.

## 2026-06-20 Polish Technical Update

New requirements now partially satisfied:

- Frontend code should continue moving from one large `page.tsx` into smaller client components and shared model helpers.
- Retrieval eval labels may specify `source_file` and use `--auto-ingest-sources` so real-world evals do not depend on manually copied local document IDs.
- Local purge must remove app-owned uploaded sources, parse-cache files, and extracted diagram directories while preserving arbitrary external local-path files.
- Linux browser-preview support should remain lightweight and avoid Electron as the default low-end path.
- Low-end mode should keep BM25/extractive fallback usable without Ollama, vector embeddings, or reranker models.

Validated:

- First frontend split passed `npm.cmd run build`.
- Real-world seed eval produced phrase-level metrics over 16 samples.
- Purge hardening passed backend tests.
- `context.md` and handoff docs are updated after the work.
- V3.1 summary cache, intent routing, and trust metadata tests pass.
- V4 golden demo script indexes bundled sources and returns citations for locked proof queries.
- Unsupported golden-demo Chat prompt returns `grounded=false` and no citations.

## 2026-06-20 Hardening Acceptance Update

New validated requirements:

- Empty or unreadable reindex attempts must fail the job without deleting prior active chunks.
- Direct local-path ingest must reject unsupported files before creating document/index records.
- Vector retrieval must not return orphaned Chroma chunks that SQLite no longer marks active.
- Broad summary/factual seed expansion must not create artificial high grounding scores.
- Exam Lab study-guide generation must use imported question-bank text for relevance checks.
- Frontend submit actions must avoid duplicate Enter submissions while a request is busy.
- Query/export metadata must snapshot the selected source at answer time.
- Startup, bootstrap, build, and packaging scripts must return non-zero on failed native commands.
- Docker Compose dev ports must remain bound to `127.0.0.1` unless a future hosted mode explicitly changes that.

Latest ship validation:

```powershell
npm.cmd run test:api
npm.cmd run compile:api
npm.cmd run build
npm.cmd run desktop:pack
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ship_check.ps1
```

All commands passed on 2026-06-20.

## 2026-06-11 Accuracy Rescue Technical Update

New technical requirements now satisfied:

- Ollama generation model must be resolved against installed local models before calling `/api/generate`.
- Generation metadata must expose requested model, used model, fallback routing, and errors in debug metadata.
- Selected-document summaries must use a cache profile version that changes when summary retrieval logic changes.
- Selected-document factual queries must augment hybrid retrieval with focused source chunks for definition and solution cues.
- Lexical retrieval must handle lightweight morphology variants without adding heavy NLP dependencies.
- Faithfulness verification must reject plausible but unsupported technique lists.

Validation commands:

```powershell
.\scripts\test_api.ps1
npm.cmd run compile:api
npm.cmd run build
```
