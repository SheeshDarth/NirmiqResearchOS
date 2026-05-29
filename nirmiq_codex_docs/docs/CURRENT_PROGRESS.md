# Current Progress — NIRMIQ ResearchOS

## Implemented

- Functional local ingestion loop
- File validation
- Idempotent ingest by content hash
- Chunk versioning
- Old chunk deactivation
- Ingestion job tracking
- BM25 lexical scoring
- Optional Chroma vector retrieval
- RRF fusion
- Lightweight rerank
- Optional Ollama embedding/rerank
- Deterministic fallback
- Grounded query path
- Retrieval metadata persistence
- Citation persistence
- Ollama generation with grounded prompt
- Fallback synthesis mode
- Retrieval evaluation script
- Recall@K
- MRR
- Citation coverage
- Session continuity
- Automatic memory snapshots
- OCR fallback for low-text pages

---

## Phase 1 Remaining

- Run full tests
- Validate migrations
- Tune retrieval defaults
- Tune context budgets
- Freeze architecture docs
- Commit stable snapshot

---

## Blocker

Codex tool usage limit blocked final pytest run.

---

## Do Not Restart

The architecture is strong.

Do not rebuild from scratch.

Continue from the current repo.
