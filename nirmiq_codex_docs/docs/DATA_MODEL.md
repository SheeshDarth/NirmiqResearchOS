# Data Model — NIRMIQ Academic Intelligence System

## SQLite Tables

### documents

```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  source_path TEXT UNIQUE NOT NULL,
  content_hash TEXT NOT NULL,
  title TEXT,
  mime_type TEXT,
  status TEXT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

---

### document_chunks

```sql
CREATE TABLE document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  index_version INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  page_start INTEGER,
  page_end INTEGER,
  text TEXT NOT NULL,
  token_count INTEGER,
  chunk_hash TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);
```

---

### sessions

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  label TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

---

### messages

```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations_json TEXT,
  retrieval_meta_json TEXT,
  created_at DATETIME NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
```

---

### memory_snapshots

```sql
CREATE TABLE memory_snapshots (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  window_start_msg_id TEXT,
  window_end_msg_id TEXT,
  created_at DATETIME NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
```

---

### ingestion_jobs

```sql
CREATE TABLE ingestion_jobs (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  stage TEXT,
  status TEXT NOT NULL,
  error TEXT,
  started_at DATETIME,
  finished_at DATETIME,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);
```

---

## Chroma Collection

Collection:
`chunks_v1`

Vector key:
`chunk_id`

Metadata:
- document_id
- index_version
- page_start
- page_end
- chunk_hash
- title

---

## Data Principles

- chunks are immutable per index version
- re-ingestion soft-disables old chunks
- content hash prevents duplicates
- document evidence must be traceable
