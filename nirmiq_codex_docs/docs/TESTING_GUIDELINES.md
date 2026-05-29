# Testing Guidelines — NIRMIQ ResearchOS

## Testing Priorities

Most important:
- retrieval correctness
- citation mapping
- ingestion idempotency
- query pipeline stability
- memory persistence

---

## Unit Tests

Test:
- chunk hashing
- content hashing
- RRF fusion
- BM25 scoring
- citation validator
- confidence scorer
- context packer

---

## Integration Tests

Test:
- ingest PDF
- create chunks
- write SQLite
- write Chroma
- query document
- generate citation
- persist message

---

## Evaluation Tests

Run:
- Recall@K
- MRR
- citation coverage
- latency profile

---

## Required Commands

```bash
python -m compileall apps/api/app
pytest
```

If pytest fails:
- fix tests
- do not bypass failures
- do not delete tests without reason
