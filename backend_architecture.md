# NIRMIQ Backend Architecture

Last updated: 2026-07-09

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
- `MemoryService`: session snapshots, continuity, thread export/delete, and local answer feedback for quality review.
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
7. When a selected document has section metadata, rank candidate sections/pages before chunk-level retrieval.
8. Expand query terms from source-local acronym definitions and section/topic metadata when available.
9. Fuse with RRF, score candidate chunks for direct answerability, and rerank/pack context.
10. Generate grounded answer or abstain.
11. Map final answer citation anchors back to the exact selected context chunks used during synthesis.
12. Run the evidence reliability gate over citation coverage, answer-used citations, verification state, and direct evidence relevance.
13. Compute citation coverage and compact trust metadata.
14. Attach Paper Lab outline/matrix/clusters for paper-draft intent.
15. Persist user/assistant turns.
16. Return answer, answer-used citations, optional debug metadata, and grounding state.

### MegaSprint One Reliability Layer

The latest reliability layer remains local-first and lightweight. The chosen architecture is documented in [`docs/nirmiq_rag_method.md`](docs/nirmiq_rag_method.md) as **NIRMIQ Evidence-First Hierarchical Hybrid RAG**:

- BM25 stays the offline retrieval backbone.
- Section/page-first ranking narrows selected-document queries when metadata exists.
- Optional vector retrieval and RRF help recall, but SQLite-confirmed active chunks remain the source of truth.
- Default `hybrid` requests are internally routed to BM25-first retrieval for attached-source academic intents because current real-world metrics show BM25 ranks textbook evidence more safely.
- Anchor rescue promotes buried direct evidence in legacy/no-section documents before synthesis.
- Query expansion is deterministic and can derive acronym expansions from the selected document instead of relying only on global prompt rules.
- Candidate priority includes an internal direct-evidence score against the original user question so explanatory answers prefer passages that define, explain, compare, or support the requested subject.
- In retrieval method version `megasprint1.v2`, direct answer relevance is weighted strongly enough to beat loose reranker/vector hits when the source passage clearly answers the question.
- Backmatter/index/glossary/example-list passages receive stronger penalties for explanatory questions.
- Synthesis receives direct-evidence metadata and fails closed when evidence is only weakly related or unrelated.
- Public query request/response shapes remain stable; additional reliability fields stay inside optional debug metadata.

### Answer Feedback

1. User rates an assistant answer as `Good` or `Needs work` from the chat bubble.
2. `POST /memory/{session_id}/feedback` stores the prompt, answer, rating, optional source document/title, reason, and timestamp in SQLite.
3. Feedback stays local and is not sent to analytics, cloud services, or model fine-tuning.
4. Clearing a session removes its feedback records.
5. Deleting a document preserves the review signal but clears the document id reference to avoid stale links.

Purpose:

- Build a real local failure/success set from Siddharth's testing.
- Feed future retrieval-evaluation labels without adding a heavy analytics stack.
- Keep answer-quality tuning grounded in actual textbook/document behavior.

## SQLite Responsibilities

- Documents and ingestion jobs.
- Document chunks and active index versions.
- Document sections for textbook-aware retrieval.
- Chunk metadata for `section_id`, `heading`, `section_path`, `chunk_type`, and `key_terms_json`.
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
- Textbook-aware section metadata and section-first retrieval diagnostics for selected-document queries.
- Debug-only retrieval metadata for section candidates, chunk-selection reasons, and retrieval diagnostics.
- Evidence reliability gate blocks `grounded=true` when final answer citations do not satisfy support checks.

## Next Backend Upgrades

- Expand the RAG Reliability Phase before adding heavier graph or agent systems.
- Convert local `Needs work` feedback into retrieval-eval candidates.
- Improve textbook section detection with page headers, captions, definition blocks, and key-term extraction.
- Tune section-first retrieval against the real-world seed set while preserving BM25-only fallback.
- SQLite concept graph tables for GraphRAG-lite only after section-first retrieval metrics plateau.
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
- `data/processed/eval/real_world_academic_seed.jsonl` adds 17 phrase-labeled questions from the Transformer paper, an ML textbook PDF, and local GenAI notes.

Linux/low-end:

- `scripts/start_local.sh` and `scripts/stop_local.sh` provide a browser-preview path for Linux.
- Low-end mode keeps Ollama generation/embeddings/reranker disabled by default, preserving BM25 plus extractive fallback behavior.

## 2026-07-11 MegaSprint Three Backend Update

Academic workflow guardrails were added for Paper Lab:

- `build_paper_lab_artifact` now prefers source-diverse retrieved evidence when multiple documents are available.
- Paper Lab debug metadata now includes source diversity, academic guardrails, and reusable section templates.
- The frontend Paper Lab Markdown export consumes those guardrails as human-readable Source Grounding Notes.
- Public `/query` request shape is unchanged.
- Normal chat UI remains unchanged and raw metadata remains hidden from the main answer flow.

Verification:

```powershell
python -m pytest apps/api/app/tests/unit/test_paper_lab.py -q
python -m pytest apps/api/app/tests/integration/test_ingest_query_flow.py -q
python -m compileall apps/api/app
npm.cmd run build
```

All commands passed on 2026-07-11.

## 2026-07-11 MegaSprint Three Exam Lab Backend Update

Exam Lab synthesis now has a deterministic marks-aware answer contract:

- 2 mark answers prefer direct answer, two key points, and source note.
- 5 mark answers add brief explanation.
- 10 mark answers add explanation, diagram note when relevant, and conclusion.
- 15 mark answers allow deeper explanation plus limitations or caveats when supported.
- The contract is injected into grounded prompts and used by the local fallback path.
- The fallback remains source-only and citation-aware; it does not add outside examples or invented diagrams.

This keeps Exam Lab useful when Ollama is unavailable or when generation is rejected by faithfulness checks.
