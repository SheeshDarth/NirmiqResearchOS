# API Contract — NIRMIQ Academic Intelligence System

## Health

### GET /health

Response:

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Ingest

### POST /ingest

Request:
- multipart file upload
- optional metadata

Response:

```json
{
  "document_id": "doc_123",
  "job_id": "job_123",
  "status": "uploaded"
}
```

---

## Documents

### GET /documents

Response:

```json
{
  "documents": [
    {
      "id": "doc_123",
      "title": "Unit 3 Notes",
      "status": "indexed",
      "created_at": "2026-05-16T10:00:00"
    }
  ]
}
```

---

## Query

### POST /query

Request:

```json
{
  "session_id": "session_123",
  "query": "Explain deadlocks for 10 marks.",
  "mode": "exam_answer",
  "retrieval_profile": "balanced",
  "debug": true
}
```

Response:

```json
{
  "answer": "Deadlock is...",
  "citations": [
    {
      "document_id": "doc_123",
      "title": "OS Unit 3",
      "page_start": 12,
      "page_end": 13,
      "chunk_id": "chunk_456"
    }
  ],
  "grounding_strength": "strong",
  "confidence": 0.86,
  "advanced": {
    "documents_used": 2,
    "retrieved_chunks": 8,
    "reranked_chunks": 5,
    "context_tokens": 1800,
    "latency_ms": 4200
  }
}
```

---

## Sessions

### POST /sessions

Creates study thread.

### GET /sessions/{session_id}

Returns session metadata.

### GET /sessions/{session_id}/messages

Returns chat history.
