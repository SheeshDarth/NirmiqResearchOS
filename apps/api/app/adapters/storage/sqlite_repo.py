import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteRepo:
    _MIGRATION_COLUMNS = {
        "document_chunks": {
            "quality_score": "REAL NOT NULL DEFAULT 1.0",
            "section_id": "TEXT",
            "heading": "TEXT",
            "section_path": "TEXT",
            "chunk_type": "TEXT NOT NULL DEFAULT 'body'",
            "key_terms_json": "TEXT",
        },
    }

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
                    quality_score REAL NOT NULL DEFAULT 1.0,
                    section_id TEXT,
                    heading TEXT,
                    section_path TEXT,
                    chunk_type TEXT NOT NULL DEFAULT 'body',
                    key_terms_json TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS document_sections (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    index_version INTEGER NOT NULL,
                    section_index INTEGER NOT NULL,
                    heading TEXT NOT NULL,
                    section_path TEXT NOT NULL,
                    page_start INTEGER,
                    page_end INTEGER,
                    key_terms_json TEXT,
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

                CREATE TABLE IF NOT EXISTS exam_profiles (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    marks INTEGER NOT NULL,
                    answer_style TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    instructions TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(session_id, document_id),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS question_bank_items (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    marks INTEGER,
                    source_label TEXT,
                    page_start INTEGER,
                    page_end INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS diagram_assets (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    image_index INTEGER NOT NULL,
                    image_path TEXT NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    caption TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(document_id, page_number, image_index),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS document_summaries (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    summary_profile TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    retrieval_meta_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(document_id, content_hash, summary_profile),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS answer_feedback (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    rating TEXT NOT NULL CHECK(rating IN ('good', 'needs_work')),
                    query TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    document_id TEXT,
                    source_title TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                """
            )
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_chunks_document_active ON document_chunks(document_id, is_active);
                CREATE INDEX IF NOT EXISTS idx_chunks_section_active ON document_chunks(section_id, is_active);
                CREATE INDEX IF NOT EXISTS idx_sections_document_active ON document_sections(document_id, is_active);
                CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_exam_profiles_session ON exam_profiles(session_id);
                CREATE INDEX IF NOT EXISTS idx_question_bank_document ON question_bank_items(document_id);
                CREATE INDEX IF NOT EXISTS idx_diagram_assets_document ON diagram_assets(document_id);
                CREATE INDEX IF NOT EXISTS idx_document_summaries_lookup
                    ON document_summaries(document_id, content_hash, summary_profile);
                CREATE INDEX IF NOT EXISTS idx_answer_feedback_session_created
                    ON answer_feedback(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_answer_feedback_rating
                    ON answer_feedback(rating);
                """
            )
            self._ensure_column(conn, "document_chunks", "quality_score", "REAL NOT NULL DEFAULT 1.0")
            self._ensure_column(conn, "document_chunks", "section_id", "TEXT")
            self._ensure_column(conn, "document_chunks", "heading", "TEXT")
            self._ensure_column(conn, "document_chunks", "section_path", "TEXT")
            self._ensure_column(conn, "document_chunks", "chunk_type", "TEXT NOT NULL DEFAULT 'body'")
            self._ensure_column(conn, "document_chunks", "key_terms_json", "TEXT")

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

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
            if not row:
                return False
            conn.execute("UPDATE answer_feedback SET document_id = NULL WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM diagram_assets WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM document_summaries WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM question_bank_items WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM exam_profiles WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM ingestion_jobs WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM document_sections WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return True

    def delete_all_documents(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id FROM documents ORDER BY updated_at DESC").fetchall()
            document_ids = [str(row["id"]) for row in rows]
            conn.execute("UPDATE answer_feedback SET document_id = NULL WHERE document_id IS NOT NULL")
            conn.execute("DELETE FROM diagram_assets")
            conn.execute("DELETE FROM document_summaries")
            conn.execute("DELETE FROM question_bank_items")
            conn.execute("DELETE FROM exam_profiles")
            conn.execute("DELETE FROM ingestion_jobs")
            conn.execute("DELETE FROM document_chunks")
            conn.execute("DELETE FROM document_sections")
            conn.execute("DELETE FROM documents")
        return document_ids

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
        query = """
            SELECT id, document_id, index_version, chunk_index, page_start, page_end,
                   text, token_count, chunk_hash, quality_score, section_id, heading,
                   section_path, chunk_type, key_terms_json, is_active, created_at
            FROM document_chunks
            WHERE document_id = ?
        """
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY chunk_index ASC, created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, (document_id,)).fetchall()
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

    def deactivate_document_sections(self, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE document_sections SET is_active = 0 WHERE document_id = ? AND is_active = 1",
                (document_id,),
            )

    def insert_document_section(
        self,
        *,
        section_id: str,
        document_id: str,
        index_version: int,
        section_index: int,
        heading: str,
        section_path: str,
        page_start: int | None,
        page_end: int | None,
        key_terms_json: str | None = None,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO document_sections (
                    id, document_id, index_version, section_index, heading, section_path,
                    page_start, page_end, key_terms_json, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    section_id,
                    document_id,
                    index_version,
                    section_index,
                    heading,
                    section_path,
                    page_start,
                    page_end,
                    key_terms_json,
                    now,
                ),
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
        quality_score: float = 1.0,
        section_id: str | None = None,
        heading: str | None = None,
        section_path: str | None = None,
        chunk_type: str = "body",
        key_terms_json: str | None = None,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            self._ensure_column(conn, "document_chunks", "quality_score", "REAL NOT NULL DEFAULT 1.0")
            self._ensure_column(conn, "document_chunks", "section_id", "TEXT")
            self._ensure_column(conn, "document_chunks", "heading", "TEXT")
            self._ensure_column(conn, "document_chunks", "section_path", "TEXT")
            self._ensure_column(conn, "document_chunks", "chunk_type", "TEXT NOT NULL DEFAULT 'body'")
            self._ensure_column(conn, "document_chunks", "key_terms_json", "TEXT")
            conn.execute(
                """
                INSERT INTO document_chunks (
                    id, document_id, index_version, chunk_index, page_start, page_end,
                    text, token_count, chunk_hash, quality_score, section_id, heading,
                    section_path, chunk_type, key_terms_json, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
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
                    quality_score,
                    section_id,
                    heading,
                    section_path,
                    chunk_type,
                    key_terms_json,
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
                SELECT id, document_id, page_start, page_end, text, token_count, quality_score,
                       section_id, heading, section_path, chunk_type, key_terms_json
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
        query = """
            SELECT id, document_id, page_start, page_end, text, token_count, quality_score,
                   section_id, heading, section_path, chunk_type, key_terms_json
            FROM document_chunks
            WHERE is_active = 1
        """
        params: tuple[str, ...] = (document_id,) if document_id else ()
        if document_id:
            query += " AND document_id = ?"
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" for _ in chunk_ids)
        query = (
            """
            SELECT id, document_id, page_start, page_end, text, token_count, quality_score,
                   section_id, heading, section_path, chunk_type, key_terms_json
            FROM document_chunks
            WHERE id IN (
            """
            + placeholders
            + """) AND is_active = 1
            """
        )
        with self._connect() as conn:
            rows = conn.execute(query, chunk_ids).fetchall()
        return {str(row["id"]): dict(row) for row in rows}

    def list_active_sections(self, document_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, document_id, index_version, section_index, heading, section_path,
                   page_start, page_end, key_terms_json, is_active, created_at
            FROM document_sections
            WHERE is_active = 1
        """
        params: tuple[str, ...] = (document_id,) if document_id else ()
        if document_id:
            query += " AND document_id = ?"
        query += " ORDER BY section_index ASC, created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

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

    def get_document_summary(
        self,
        *,
        document_id: str,
        content_hash: str,
        summary_profile: str,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, document_id, content_hash, summary_profile, answer,
                       citations_json, retrieval_meta_json, created_at, updated_at
                FROM document_summaries
                WHERE document_id = ? AND content_hash = ? AND summary_profile = ?
                """,
                (document_id, content_hash, summary_profile),
            ).fetchone()
        return dict(row) if row else None

    def upsert_document_summary(
        self,
        *,
        summary_id: str,
        document_id: str,
        content_hash: str,
        summary_profile: str,
        answer: str,
        citations_json: str,
        retrieval_meta_json: str,
    ) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO document_summaries (
                    id, document_id, content_hash, summary_profile, answer,
                    citations_json, retrieval_meta_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id, content_hash, summary_profile) DO UPDATE SET
                    answer = excluded.answer,
                    citations_json = excluded.citations_json,
                    retrieval_meta_json = excluded.retrieval_meta_json,
                    updated_at = excluded.updated_at
                """,
                (
                    summary_id,
                    document_id,
                    content_hash,
                    summary_profile,
                    answer,
                    citations_json,
                    retrieval_meta_json,
                    now,
                    now,
                ),
            )

    def get_document_summary_count(self, document_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM document_summaries WHERE document_id = ?",
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

    def insert_answer_feedback(
        self,
        *,
        feedback_id: str,
        session_id: str,
        rating: str,
        query: str,
        answer: str,
        document_id: str | None = None,
        source_title: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        now = self._utc_now()
        self.ensure_session(session_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO answer_feedback (
                    id, session_id, rating, query, answer, document_id, source_title, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    session_id,
                    rating,
                    query,
                    answer,
                    document_id,
                    source_title,
                    reason,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT id, session_id, rating, query, answer, document_id, source_title, reason, created_at
                FROM answer_feedback
                WHERE id = ?
                """,
                (feedback_id,),
            ).fetchone()
        return dict(row)

    def list_answer_feedback(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, rating, query, answer, document_id, source_title, reason, created_at
                FROM answer_feedback
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_answer_feedback_count(self, session_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM answer_feedback WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def delete_session(self, session_id: str) -> dict[str, int | bool]:
        with self._connect() as conn:
            message_row = conn.execute(
                "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            snapshot_row = conn.execute(
                "SELECT COUNT(*) AS count FROM memory_snapshots WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            session_row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            deleted_messages = int(message_row["count"]) if message_row else 0
            deleted_snapshots = int(snapshot_row["count"]) if snapshot_row else 0
            conn.execute("DELETE FROM answer_feedback WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM memory_snapshots WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return {
            "deleted": bool(session_row or deleted_messages or deleted_snapshots),
            "deleted_messages": deleted_messages,
            "deleted_snapshots": deleted_snapshots,
        }

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

    def upsert_exam_profile(
        self,
        profile_id: str,
        session_id: str,
        document_id: str,
        title: str,
        marks: int,
        answer_style: str,
        content_type: str,
        instructions: str | None,
    ) -> dict[str, Any]:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO exam_profiles (
                    id, session_id, document_id, title, marks, answer_style,
                    content_type, instructions, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, document_id) DO UPDATE SET
                    title = excluded.title,
                    marks = excluded.marks,
                    answer_style = excluded.answer_style,
                    content_type = excluded.content_type,
                    instructions = excluded.instructions,
                    updated_at = excluded.updated_at
                """,
                (
                    profile_id,
                    session_id,
                    document_id,
                    title,
                    marks,
                    answer_style,
                    content_type,
                    instructions,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT id, session_id, document_id, title, marks, answer_style,
                       content_type, instructions, created_at, updated_at
                FROM exam_profiles
                WHERE session_id = ? AND document_id = ?
                """,
                (session_id, document_id),
            ).fetchone()
        return dict(row)

    def list_exam_profiles(self, session_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, session_id, document_id, title, marks, answer_style,
                   content_type, instructions, created_at, updated_at
            FROM exam_profiles
        """
        params: tuple[str, ...] = (session_id,) if session_id else ()
        if session_id:
            query += " WHERE session_id = ?"
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def replace_question_bank_items(self, document_id: str, items: list[dict[str, Any]]) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute("DELETE FROM question_bank_items WHERE document_id = ?", (document_id,))
            conn.executemany(
                """
                INSERT INTO question_bank_items (
                    id, document_id, question, marks, source_label, page_start, page_end, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item["id"],
                        document_id,
                        item["question"],
                        item.get("marks"),
                        item.get("source_label"),
                        item.get("page_start"),
                        item.get("page_end"),
                        now,
                    )
                    for item in items
                ],
            )

    def list_question_bank_items(self, document_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, document_id, question, marks, source_label, page_start, page_end, created_at
                FROM question_bank_items
                WHERE document_id = ?
                ORDER BY created_at ASC
                """,
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def insert_diagram_asset(
        self,
        asset_id: str,
        document_id: str,
        page_number: int,
        image_index: int,
        image_path: str,
        width: int | None,
        height: int | None,
        caption: str | None,
    ) -> dict[str, Any]:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO diagram_assets (
                    id, document_id, page_number, image_index, image_path,
                    width, height, caption, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id, page_number, image_index) DO UPDATE SET
                    image_path = excluded.image_path,
                    width = excluded.width,
                    height = excluded.height,
                    caption = excluded.caption
                """,
                (
                    asset_id,
                    document_id,
                    page_number,
                    image_index,
                    image_path,
                    width,
                    height,
                    caption,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT id, document_id, page_number, image_index, image_path,
                       width, height, caption, created_at
                FROM diagram_assets
                WHERE document_id = ? AND page_number = ? AND image_index = ?
                """,
                (document_id, page_number, image_index),
            ).fetchone()
        return dict(row)

    def list_diagram_assets(self, document_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, document_id, page_number, image_index, image_path,
                       width, height, caption, created_at
                FROM diagram_assets
                WHERE document_id = ?
                ORDER BY page_number ASC, image_index ASC
                """,
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_diagram_asset(self, asset_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, document_id, page_number, image_index, image_path,
                       width, height, caption, created_at
                FROM diagram_assets
                WHERE id = ?
                """,
                (asset_id,),
            ).fetchone()
        return dict(row) if row else None

    def delete_diagram_assets(self, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM diagram_assets WHERE document_id = ?", (document_id,))

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        expected_definition = SQLiteRepo._MIGRATION_COLUMNS.get(table, {}).get(column)
        if expected_definition != definition:
            raise ValueError("Refusing unsafe SQLite migration column definition.")
        table_sql = SQLiteRepo._quote_identifier(table)
        column_sql = SQLiteRepo._quote_identifier(column)
        existing = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(" + table_sql + ")").fetchall()
        }
        if column not in existing:
            conn.execute("ALTER TABLE " + table_sql + " ADD COLUMN " + column_sql + " " + definition)

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        if not identifier.replace("_", "").isalnum():
            raise ValueError("Unsafe SQLite identifier.")
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        sanitized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
        return [token for token in sanitized.split() if token]
