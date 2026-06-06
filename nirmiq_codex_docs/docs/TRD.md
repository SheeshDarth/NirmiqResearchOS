# Technical Requirements Document — NIRMIQ Academic Intelligence System

## Technical Goal

Build an offline-first, low-hallucination document intelligence chatbot optimized for student academic workflows.

---

## Current Architecture

Single-process FastAPI backend with modular internal services.

Frontend:
- Next.js PWA

Backend:
- FastAPI

Persistence:
- SQLite
- ChromaDB

Models:
- Ollama for local generation and embeddings
- nomic-embed-text for embeddings
- Phi-3 Mini for general generation
- DeepSeek Coder 6.7B for coding-heavy queries
- bge-reranker-base for reranking

Parsing:
- PyMuPDF
- OCR fallback via Tesseract

---

## Core Pipeline

```text
Upload
  ↓
Document Validation
  ↓
Raw File Storage
  ↓
Text Parsing
  ↓
OCR Fallback
  ↓
Text Normalization
  ↓
Chunking
  ↓
SQLite Chunk Storage
  ↓
Embedding
  ↓
Chroma Upsert
  ↓
BM25 Index Update
  ↓
Queryable Knowledge Base
```

---

## Query Pipeline

```text
User Query
  ↓
Session Memory Fetch
  ↓
Query Normalization
  ↓
BM25 Retrieval
  ↓
Vector Retrieval
  ↓
RRF Fusion
  ↓
Reranking
  ↓
Context Compression
  ↓
Citation Map
  ↓
Grounded Prompt
  ↓
Local Generation
  ↓
Citation Validation
  ↓
Confidence Scoring
  ↓
Response
```

---

## Backend Layers

### API Layer

Folder:
`apps/api/app/api/routers`

Responsibilities:
- validate HTTP input
- call service layer
- return response DTOs

Must not:
- perform retrieval
- run model logic
- contain business rules

---

### Service Layer

Folder:
`apps/api/app/services`

Services:
- IngestionService
- IndexingService
- RetrievalService
- MemoryService
- SynthesisService
- QueryService

Responsibilities:
- orchestrate use cases
- compose adapters
- enforce policies

---

### Domain Layer

Folder:
`apps/api/app/domain`

Responsibilities:
- pure models
- retrieval policies
- citation rules
- confidence enums
- guardrail thresholds

---

### Adapter Layer

Folder:
`apps/api/app/adapters`

Responsibilities:
- external library integrations
- SQLite repositories
- Chroma repository
- Ollama client
- PyMuPDF parser
- BM25 index
- reranker
- generator

---

## SQLite Schema

Tables:
- documents
- document_chunks
- sessions
- messages
- memory_snapshots
- ingestion_jobs

Refer to:
`docs/DATA_MODEL.md`

---

## Required API Endpoints

### Health

`GET /health`

Returns service health.

---

### Ingest

`POST /ingest`

Uploads or registers a document.

Returns:
- document_id
- job_id
- status

---

### Documents

`GET /documents`

Lists indexed documents.

`GET /documents/{document_id}`

Shows document metadata.

---

### Query

`POST /query`

Accepts:
- session_id
- user query
- mode
- debug flag

Returns:
- answer
- citations
- grounding strength
- confidence
- retrieval metadata if debug enabled

---

### Memory

`GET /sessions/{session_id}`

Returns session metadata.

`GET /sessions/{session_id}/messages`

Returns chat history.

---

## Retrieval Requirements

Hybrid retrieval is mandatory.

Use:
- BM25 top-K
- Chroma top-K
- Reciprocal Rank Fusion
- reranking top-N
- token-budget context packing

Do not use vector-only retrieval as final system.

---

## Grounding Requirements

Generated answer must:
- use supplied context only
- cite supporting chunks
- avoid unsupported claims
- abstain when weak evidence
- expose confidence metadata

---

## Performance Requirements

Optimize for:
- RTX 4050 laptop
- low VRAM
- local inference
- limited memory
- student laptop usage

Do not co-run:
- reranker GPU
- large generator GPU

unless explicitly configured.

---

## MVP Exit Criteria

MVP is ready when:
- user uploads a PDF
- system indexes it
- user asks question
- system retrieves hybrid context
- answer includes citations
- confidence is shown
- evidence panel displays sources
- low evidence causes abstention
