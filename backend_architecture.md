# NIRMIQ Backend Architecture

Last updated: 2026-06-02

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

- `IngestionService`: accepts source paths/uploads, enforces local corpus roots, validates upload signatures, creates document records, runs parsing/indexing.
- `IndexingService`: chunks parsed pages, persists chunks, updates lexical/vector indexes.
- `RetrievalService`: BM25/vector retrieval, RRF fusion, optional reranking, citation assembly.
- `SynthesisService`: grounded response generation, summary formatting, fallback behavior, abstention.
- `QueryService`: end-to-end query orchestration, mode/profile handling, memory writes.
- `MemoryService`: session snapshots and continuity.
- `DocumentsService`: library and chunk drilldown.
- `ExamService`: exam profiles, question banks, and exam-specific artifacts.

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
4. Retrieve candidates from BM25 and optional vector search.
5. Fuse with RRF and rerank/pack context.
6. Generate grounded answer or abstain.
7. Persist user/assistant turns.
8. Return answer, citations, debug metadata, and grounding state.

## SQLite Responsibilities

- Documents and ingestion jobs.
- Document chunks and active index versions.
- Sessions and messages.
- Memory snapshots.
- Exam profiles and question banks.
- Diagram/image metadata as the project expands.

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

## Next Backend Upgrades

- Document-level summary cache.
- SQLite concept graph tables for GraphRAG-lite.
- Source diversity controls for Paper Lab.
- Local data purge/export endpoints.
- Optional local agent orchestrator with explicit tool allowlists and approval gates.
