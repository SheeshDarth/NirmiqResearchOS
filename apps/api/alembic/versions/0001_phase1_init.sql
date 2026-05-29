-- Phase 1 bootstrap schema for local SQLite.
-- Kept as plain SQL for transparency and easy debugging.

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_path TEXT UNIQUE NOT NULL,
    content_hash TEXT NOT NULL,
    title TEXT,
    mime_type TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    index_version INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    label TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    citations_json TEXT,
    retrieval_meta_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS memory_snapshots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    window_start_msg_id TEXT,
    window_end_msg_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

