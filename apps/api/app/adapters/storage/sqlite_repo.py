import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteRepo:
    def __init__(self, sqlite_path: Path) -> None:
        self._sqlite_path = sqlite_path
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
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

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    label TEXT,
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
                """
            )
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_chunks_document_active ON document_chunks(document_id, is_active);
                CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);
                """
            )

    def insert_document(
        self,
        document_id: str,
        source_path: str,
        content_hash: str,
        title: str | None,
        mime_type: str | None,
        status: str,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, source_path, content_hash, title, mime_type, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, source_path, content_hash, title, mime_type, status, now, now),
            )

    def get_document_by_source_path(self, source_path: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_path, content_hash, title, mime_type, status, created_at, updated_at
                FROM documents WHERE source_path = ?
                """,
                (source_path,),
            ).fetchone()
        return dict(row) if row else None

    def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_path, content_hash, title, mime_type, status, created_at, updated_at
                FROM documents WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT d.id, d.title, d.status, d.source_path, d.updated_at,
                       COALESCE(SUM(CASE WHEN c.is_active = 1 THEN 1 ELSE 0 END), 0) AS active_chunk_count
                FROM documents d
                LEFT JOIN document_chunks c ON c.document_id = d.id
                GROUP BY d.id, d.title, d.status, d.source_path, d.updated_at
                ORDER BY d.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_document_chunks(self, document_id: str, active_only: bool = True) -> list[dict[str, Any]]:
        active_filter = "AND is_active = 1" if active_only else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, document_id, index_version, chunk_index, page_start, page_end,
                       text, token_count, chunk_hash, is_active, created_at
                FROM document_chunks
                WHERE document_id = ? {active_filter}
                ORDER BY chunk_index ASC, created_at ASC
                """,
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_document_status(self, document_id: str, status: str) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, document_id),
            )

    def update_document_metadata(
        self,
        document_id: str,
        content_hash: str,
        title: str | None,
        mime_type: str | None,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET content_hash = ?, title = ?, mime_type = ?, updated_at = ?
                WHERE id = ?
                """,
                (content_hash, title, mime_type, now, document_id),
            )

    def insert_ingestion_job(self, job_id: str, document_id: str, stage: str, status: str) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_jobs (id, document_id, stage, status, error, started_at, finished_at)
                VALUES (?, ?, ?, ?, NULL, ?, NULL)
                """,
                (job_id, document_id, stage, status, now),
            )

    def update_ingestion_job(
        self, job_id: str, stage: str, status: str, error: str | None = None
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ingestion_jobs
                SET stage = ?, status = ?, error = ?, finished_at = ?
                WHERE id = ?
                """,
                (stage, status, error, now, job_id),
            )

    def get_latest_ingestion_job(self, document_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, document_id, stage, status, error, started_at, finished_at
                FROM ingestion_jobs
                WHERE document_id = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_ingestion_jobs(self, document_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, document_id, stage, status, error, started_at, finished_at
                FROM ingestion_jobs
                WHERE document_id = ?
                ORDER BY started_at DESC
                """,
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_next_index_version(self, document_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(index_version), 0) AS max_version FROM document_chunks WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return int(row["max_version"]) + 1 if row else 1

    def deactivate_document_chunks(self, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE document_chunks SET is_active = 0 WHERE document_id = ? AND is_active = 1",
                (document_id,),
            )

    def insert_document_chunk(
        self,
        chunk_id: str,
        document_id: str,
        index_version: int,
        chunk_index: int,
        page_start: int | None,
        page_end: int | None,
        text: str,
        token_count: int,
        chunk_hash: str,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO document_chunks (
                    id, document_id, index_version, chunk_index, page_start, page_end,
                    text, token_count, chunk_hash, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    chunk_id,
                    document_id,
                    index_version,
                    chunk_index,
                    page_start,
                    page_end,
                    text,
                    token_count,
                    chunk_hash,
                    now,
                ),
            )

    def search_active_chunks(self, query: str, limit: int) -> list[dict[str, Any]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, document_id, page_start, page_end, text, token_count
                FROM document_chunks
                WHERE is_active = 1
                """
            ).fetchall()

        scored: list[tuple[float, dict[str, Any]]] = []
        token_set = set(tokens)
        for row in rows:
            item = dict(row)
            chunk_tokens = set(self._tokenize(item["text"]))
            overlap = token_set.intersection(chunk_tokens)
            if not overlap:
                continue
            score = len(overlap) / max(len(token_set), 1)
            item["score"] = score
            scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def list_active_chunks(self, document_id: str | None = None) -> list[dict[str, Any]]:
        document_filter = "AND document_id = ?" if document_id else ""
        params: tuple[str, ...] = (document_id,) if document_id else ()
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, document_id, page_start, page_end, text, token_count
                FROM document_chunks
                WHERE is_active = 1 {document_filter}
                ORDER BY created_at DESC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" for _ in chunk_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, document_id, page_start, page_end, text, token_count
                FROM document_chunks
                WHERE id IN ({placeholders}) AND is_active = 1
                """,
                chunk_ids,
            ).fetchall()
        return {str(row["id"]): dict(row) for row in rows}

    def get_active_chunk_count(self, document_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM document_chunks
                WHERE document_id = ? AND is_active = 1
                """,
                (document_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def ensure_session(self, session_id: str) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions (id, label, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, None, now, now),
            )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

    def insert_message(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        citations_json: str | None = None,
        retrieval_meta_json: str | None = None,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, session_id, role, content, citations_json, retrieval_meta_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, citations_json, retrieval_meta_json, now),
            )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

    def get_session_summary(self, session_id: str) -> tuple[str, int]:
        snapshot = self.get_latest_memory_snapshot(session_id)
        count = self.get_session_message_count(session_id)
        if snapshot:
            summary = str(snapshot["summary"])
        else:
            summary = "No memory summary yet." if count == 0 else f"{count} messages in session."
        return summary, count

    def get_session_message_count(self, session_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def get_latest_message(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_recent_messages(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        ordered = [dict(row) for row in rows]
        ordered.reverse()
        return ordered

    def get_session_messages(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, role, content, citations_json, retrieval_meta_json, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
        """
        params: list[Any] = [session_id]
        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        ordered = [dict(row) for row in rows]
        ordered.reverse()
        return ordered

    def get_latest_memory_snapshot(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, session_id, summary, window_start_msg_id, window_end_msg_id, created_at
                FROM memory_snapshots
                WHERE session_id = ?
            ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def insert_memory_snapshot(
        self,
        snapshot_id: str,
        session_id: str,
        summary: str,
        window_start_msg_id: str | None,
        window_end_msg_id: str | None,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_snapshots (
                    id, session_id, summary, window_start_msg_id, window_end_msg_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, session_id, summary, window_start_msg_id, window_end_msg_id, now),
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        sanitized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
        return [token for token in sanitized.split() if token]
