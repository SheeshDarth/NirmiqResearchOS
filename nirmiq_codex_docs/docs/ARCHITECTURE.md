# Architecture — NIRMIQ ResearchOS

## Architecture Style

Modular monolith.

Why:
- solo developer friendly
- offline-first
- easy debugging
- no network complexity
- simpler deployment

---

## Repository Structure

```text
Nirmiq-researchOS/
├─ apps/
│  ├─ api/
│  └─ web/
├─ packages/
├─ data/
├─ models/
├─ scripts/
├─ docs/
├─ prompts/
├─ evaluation/
├─ AGENTS.md
└─ README.md
```

---

## Backend Structure

```text
apps/api/app/
├─ main.py
├─ core/
├─ api/
│  ├─ routers/
│  └─ schemas/
├─ domain/
├─ services/
├─ adapters/
├─ pipelines/
└─ tests/
```

---

## Main Services

### IngestionService

Handles:
- file validation
- duplicate detection
- job tracking
- raw storage

---

### IndexingService

Handles:
- parsing
- chunking
- embeddings
- Chroma writes
- BM25 writes

---

### RetrievalService

Handles:
- BM25 retrieval
- vector retrieval
- RRF fusion
- reranking
- context packing
- citation bundle

---

### MemoryService

Handles:
- sessions
- messages
- summaries
- recent context

Memory cannot override source evidence.

---

### SynthesisService

Handles:
- grounded prompt creation
- local generation
- answer formatting
- citation enforcement

---

### QueryService

End-to-end orchestration:
- load memory
- retrieve context
- generate answer
- validate citations
- save turn

---

## Advanced Section Architecture

The UI includes an advanced research panel.

It should show:
- documents used
- retrieved chunks
- grounding strength
- confidence score
- related concepts
- token budget
- retrieval profile
- citations

This panel is read-only for MVP.

---

## Design Constraint

NIRMIQ is a chatbot interface with an academic evidence system.

The chat is the primary UX.

The advanced panel is the trust layer.
