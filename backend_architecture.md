# NIRMIQ Backend Architecture

Last updated: 2026-06-22

## Overview

The backend is a single FastAPI service with modular internals. This keeps the MVP simple for a solo developer while preserving clean boundaries for retrieval, ingestion, memory, exams, and synthesis.

## Runtime Surfaces

- `apps/web`: primary Next.js interface for Research, Chat, Paper Lab, Exam Lab, uploads, citations, and local data controls.
- `apps/api`: local FastAPI runtime for ingestion, retrieval, synthesis, memory, and exports.
- `apps/desktop`: lightweight Electron shell that starts the same local API/web runtime, opens NIRMIQ in a Windows app window, and exposes developer-friendly shortcuts for logs, VS Code, project docs, runtime status, and local data.

The desktop shell is intentionally not a second application layer. It preserves the offline-first architecture and keeps all product logic in the existing API/web stack.

## Layering

- Routers: HTTP validation and response shape only.
- Schemas: typed request and response contracts.
- Services: orchestration and business flow.
- Domain: pure policies and shared models.
- Adapters: SQLite, Chroma, PyMuPDF, OCR, Ollama, BM25, RRF.
- Pipelines: thin end-to-end wrappers for ingestion/query lifecycles.

## Service Boundaries

- `HealthRouter`: liveness and local demo readiness checks.
- `IngestionService`: accepts source paths/uploads, enforces local corpus roots, validates upload signatures, creates document records, runs parsing/indexing.
- `IndexingService`: chunks parsed pages, persists chunks, updates lexical/vector indexes.
- `RetrievalService`: BM25/vector retrieval, RRF fusion, optional reranking, citation assembly.
- `SynthesisService`: grounded response generation, summary formatting, citation coverage, fallback behavior, abstention.
- `QueryService`: end-to-end query orchestration, intent routing, summary cache orchestration, mode/profile handling, memory writes.
- `MemoryService`: session snapshots and continuity.
- `DocumentsService`: library and chunk drilldown.
- `Local Data Controls`: thread export/delete and document-index purge through existing memory/document services.
- `ExamService`: exam profiles, question banks, and exam-specific artifacts.

## API Surface

The backend preserves the original local MVP routes while also exposing `/api/v1` aliases for future clients.

Examples:

- Legacy: `GET /health`
- Versioned: `GET /api/v1/health`
- Legacy: `POST /query`
- Versioned: `POST /api/v1/query`

This keeps the current frontend stable while addressing API-versioning readiness.

## Data Lifecycle

### Ingestion

1. Receive file upload or local path.
2. Validate file type and local-path privacy boundaries.
3. Copy/store source in `data/raw` when uploaded.
4. Parse PDF/text/image content.
5. Cache parsed PDF pages by content hash.
6. Create deterministic chunks.
7. Store chunks in SQLite.
8. Update BM25 index and optional Chroma vectors.
9. Mark document indexed.

### Query

1. Receive prompt, mode, retrieval mode, profile, and session id.
2. Load session memory.
3. Normalize and route prompt intent.
4. Return cached selected-document summary when the document hash/profile matches.
5. Expand retrieval query internally for summary, factual lookup, comparison, paper, deep research, and exam intents.
6. Retrieve candidates from BM25 and optional vector search.
7. Fuse with RRF and rerank/pack context.
8. Generate grounded answer or abstain.
9. Map final answer citation anchors back to the exact selected context chunks used during synthesis.
10. Compute citation coverage and trust metadata.
11. Attach Paper Lab outline/matrix/clusters for paper-draft intent.
12. Persist user/assistant turns.
13. Return answer, answer-used citations, optional debug metadata, and grounding state.

## SQLite Responsibilities

- Documents and ingestion jobs.
- Document chunks and active index versions.
- Sessions and messages.
- Memory snapshots.
- Exam profiles and question banks.
- Diagram/image metadata as the project expands.
- Document summary cache keyed by document id, content hash, and summary profile.
- Schema migrations use allowlisted identifiers rather than user-controlled dynamic SQL.

## Chroma Responsibilities

- Optional semantic vector retrieval.
- Must not be required for the app to work.
- Tests use isolated temporary Chroma paths.

## Local Inference Strategy

- Use Ollama when available.
- Keep generation, embedding, and reranking independently toggleable.
- Fall back to deterministic embeddings and extractive synthesis when local models are unavailable.
- Avoid loading multiple heavy models at once on RTX 4050 hardware.
- Use adaptive generation temperature: low for factual grounded answers, higher only for long-context deep research and drafting.
- Run citation-faithfulness verification after generated answers before returning them to the user.
- Bound Ollama runtime options by default: short keep-alive, 3072 context, 768 prediction cap, optional GPU/thread controls, and batched embeddings.

## Current Optimizations

- Parsed PDF page cache by content hash.
- Summary mode for broad document prompts.
- Document-scoped fallback retrieval.
- Retrieval profiles for fast/balanced/precision behavior.
- Compact frontend source cockpit to reduce unnecessary backend calls.
- Chunk quality scoring and retrieval quality weighting.
- Citation verification with fallback rewrite for unsupported claims.
- Public citations are filtered to final answer-used context chunks, not the full retrieval bundle.
- Backend intent routing now owns exam-style language and factual query expansion, reducing reliance on frontend mode selection.
- Factual selected-document prompts add focused retrieval hints for definitions, examples, algorithms, limitations, and common ML families such as unsupervised learning.
- Fallback synthesis uses a compact answer contract for list/algorithm questions: direct answer, key points, evidence note.
- Local ingestion allowlists and upload content sniffing.
- Adaptive long-context temperature for deep research and drafting.
- SQLite-backed selected-document summary cache.
- Deterministic query intent router and retrieval hint expansion.
- Citation coverage metadata and compact UI trust badge.
- Paper Lab deterministic related-work matrix, citation clusters, outline metadata, and Markdown export.
- Low-memory local model profile exposed through readiness metadata.
- Request body size enforcement before large local uploads are processed.
- Response compression for larger local API payloads.
- Production-only HSTS/CSP toggles that remain disabled on localhost by default.
- Thread Markdown export, session memory deletion, and indexed-material purge for local privacy/reviewer demos.
- Indexed-material purge removes app-owned uploaded files, parse-cache files, and extracted diagram directories while preserving arbitrary external local-path sources.
- Electron desktop shell with local runtime startup, diagnostics menu, log access, and portable Windows packaging path.

## Next Backend Upgrades

- SQLite concept graph tables for GraphRAG-lite.
- Multi-document source diversity controls for Paper Lab.
- Local data purge/export endpoints.
- Optional local agent orchestrator with explicit tool allowlists and approval gates.
- Optional local bug-report bundle export instead of cloud error tracking.

## 2026-06-11 Accuracy Rescue Architecture Update

The query lifecycle now includes two selected-document context augmentation steps before synthesis:

1. Summary seed augmentation for selected-document summary intent.
2. Focused factual seed augmentation for selected-document definition/solution/exam/deep-research style prompts.

Updated query lifecycle:

1. Receive prompt and selected document.
2. Detect deterministic intent.
3. Resolve retrieval profile and mode.
4. Return cached selected-document summary only when the summary profile and content hash match.
5. Run hybrid retrieval.
6. Drop vector hits that are no longer active in SQLite.
7. Add summary/factual seed chunks when applicable, using low seed scores so they expand context without inflating grounding confidence.
8. Synthesize with the best installed local generation model.
9. Anchor uncited generated sentences only when source support is strong enough.
10. Verify cited claims conservatively.
11. Rewrite to source-only fallback when unsupported specific claims are detected.
12. Return trust metadata and citations.

Model routing:

- The generator now discovers installed Ollama models and records requested versus used model metadata.
- `mistral:7b-instruct-q4_K_M` is preferred for answer text on this machine because `qwen3.5:4b` returned empty response text under the tested generation budget.
- Embedding and reranking remain independently toggleable.

Retrieval changes:

- BM25 and lexical reranker now apply light stemming for common English morphology.
- Summary prompts seed context with early outline-like chunks.
- Factual selected-document prompts seed context with chunks that contain focus terms plus definition/solution cues.
- Exam Lab study-guide relevance checks use imported question-bank text instead of generic UI command words.
- Vector-only retrieval no longer rehydrates chunks from Chroma metadata unless SQLite confirms the chunk is active.
- Vector and BM25-only scores are normalized to avoid rank-derived score inflation.

Trust behavior:

- Generated answers are not trusted just because they have citations.
- Unsupported specific claims trigger source-only rewrite.
- Stale `indexed` documents with no active chunks are surfaced as `needs_reindex` in the library API.

## 2026-06-20 Hardening Audit Update

Additional reliability fixes implemented after multi-agent review:

- `IndexingService` fails early when parsing returns zero readable chunks, preserving prior active chunks during failed reindex attempts.
- `IngestionService` validates direct local paths with the same file suffix, size, and lightweight signature/readability checks used for uploads.
- `RetrievalService` filters fused candidates to active SQLite chunks and records `orphan_vector_hits_dropped`.
- `QueryService` summary/factual seed chunks now use low expansion scores rather than artificial high scores.
- `SynthesisService` requires relevance for non-overview modes, rewrites on any unsupported cited claim, and avoids fabricating fallback anchors.
- Study-guide synthesis relevance now includes imported question-bank text for Exam Lab flows.
- Frontend query calls are scoped to the selected document when one is active, use timeouts, prevent Enter double-submit while busy, and snapshot source metadata per answer/export.
- Windows runtime scripts now check native exit codes, use `npm.cmd`, separate normal preview from golden-demo preview, and stop desktop-launched child processes more reliably.
- Docker Compose local ports bind to loopback only.

Latest validation:

- `npm.cmd run test:api`: `41 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.
- `npm.cmd run desktop:pack`: passed.
- `docker compose -f docker-compose.local.yml config`: passed with expected user-level Docker config permission warning.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ship_check.ps1`: passed.

## 2026-06-20 Polish Sprint Update

Frontend maintainability:

- `apps/web/app/page.tsx` was split into:
  - `apps/web/app/page-model.ts` for shared types, constants, helpers, export builders, diffing, trust labels, and guide parsing.
  - `apps/web/components/local-login.tsx` for first-run local profile UI.
  - `apps/web/components/study-guide-answer.tsx` for Exam Lab study-guide rendering.
- The main page still owns orchestration/state and should be split further into sidebar, thread, composer, and Deep Research components later.

Evaluation:

- `scripts/eval_retrieval.py` now supports `source_file` labels and `--auto-ingest-sources`.
- `scripts/eval_real_world.ps1` evaluates real local academic material without manual document-id copying.
- `data/processed/eval/real_world_academic_seed.jsonl` adds 16 phrase-labeled questions from the Transformer paper, an ML textbook PDF, and local GenAI notes.

Linux/low-end:

- `scripts/start_local.sh` and `scripts/stop_local.sh` provide a browser-preview path for Linux.
- Low-end mode keeps Ollama generation/embeddings/reranker disabled by default, preserving BM25 plus extractive fallback behavior.
