# NIRMIQ Backend Architecture

Last updated: 2026-06-14

## Overview

The backend is a single FastAPI service with modular internals. This keeps the MVP simple for a solo developer while preserving clean boundaries for retrieval, ingestion, memory, exams, and synthesis.

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
5. Retrieve candidates from BM25 and optional vector search.
6. Fuse with RRF and rerank/pack context.
7. Generate grounded answer or abstain.
8. Compute citation coverage and trust metadata.
9. Attach Paper Lab outline/matrix/clusters for paper-draft intent.
10. Persist user/assistant turns.
11. Return answer, citations, debug metadata, and grounding state.

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
6. Add summary/factual seed chunks when applicable.
7. Synthesize with the best installed local generation model.
8. Anchor uncited generated sentences to source chunks.
9. Verify cited claims conservatively.
10. Rewrite to source-only fallback when unsupported specific claims are detected.
11. Return trust metadata and citations.

Model routing:

- The generator now discovers installed Ollama models and records requested versus used model metadata.
- `mistral:7b-instruct-q4_K_M` is preferred for answer text on this machine because `qwen3.5:4b` returned empty response text under the tested generation budget.
- Embedding and reranking remain independently toggleable.

Retrieval changes:

- BM25 and lexical reranker now apply light stemming for common English morphology.
- Summary prompts seed context with early outline-like chunks.
- Factual selected-document prompts seed context with chunks that contain focus terms plus definition/solution cues.

Trust behavior:

- Generated answers are not trusted just because they have citations.
- Unsupported specific claims trigger source-only rewrite.
- Stale `indexed` documents with no active chunks are surfaced as `needs_reindex` in the library API.
