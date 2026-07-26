import sqlite3
from pathlib import Path

from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.services.indexing_service import IndexingService


def test_section_detection_extracts_textbook_headings_and_key_terms() -> None:
    pages = [
        (
            1,
            "\n".join(
                [
                    "Chapter 1 Machine Learning Basics",
                    "Machine learning systems learn patterns from data.",
                    "1.1 Unsupervised Learning",
                    "Unsupervised learning includes clustering, dimensionality reduction, and anomaly detection.",
                ]
            ),
        )
    ]

    service = IndexingService.__new__(IndexingService)
    service._chunk_tokens = 180
    service._chunk_overlap = 30
    sections = service._section_pages(pages)
    chunks = service._chunk_sections(sections)

    headings = [section.heading for section in sections]
    assert "Chapter 1 Machine Learning Basics" in headings
    assert "1.1 Unsupervised Learning" in headings
    assert any("clustering" in section.key_terms for section in sections)
    assert chunks
    assert chunks[-1].section_path == "1.1 Unsupervised Learning"


def test_ocr_page_fragments_are_coalesced_into_bounded_evidence() -> None:
    service = IndexingService.__new__(IndexingService)
    service._chunk_tokens = 180
    service._chunk_overlap = 30
    service._ocr_applied_pages = {1}
    pages = [
        (
            1,
            "\n".join(
                [
                    "PIPELINE STEPS",
                    "Brief Reference Build Style",
                    "Assets Animations Optimize Deploy",
                    "The guide turns a visual reference into a deployable website.",
                ]
            ),
        )
    ]

    sections = service._section_pages(pages)
    chunks = service._chunk_sections(sections)

    assert len(sections) == 1
    assert "Brief Reference" in sections[0].text
    assert "deployable website" in chunks[0].text
    assert len(chunks[0].text.split()) <= 320


def test_sqlite_chunk_section_metadata_is_additive(tmp_path: Path) -> None:
    repo = SQLiteRepo(tmp_path / "nirmiq.db")
    repo.init_db()
    repo.insert_document(
        document_id="doc-1",
        source_path=str(tmp_path / "source.txt"),
        content_hash="hash-1",
        title="Source",
        mime_type="text/plain",
        status="indexed",
    )
    repo.insert_document_section(
        section_id="section-1",
        document_id="doc-1",
        index_version=1,
        section_index=0,
        heading="Chapter 1 Retrieval",
        section_path="Chapter 1 Retrieval",
        page_start=1,
        page_end=2,
        key_terms_json='["retrieval","citations"]',
    )
    repo.insert_document_chunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        index_version=1,
        chunk_index=0,
        page_start=1,
        page_end=1,
        text="Retrieval uses citations to ground answers.",
        token_count=7,
        chunk_hash="chunk-hash",
        section_id="section-1",
        heading="Chapter 1 Retrieval",
        section_path="Chapter 1 Retrieval",
        chunk_type="definition",
        key_terms_json='["retrieval","citations"]',
    )

    chunks = repo.get_document_chunks("doc-1")
    assert chunks[0]["section_id"] == "section-1"
    assert chunks[0]["heading"] == "Chapter 1 Retrieval"
    assert chunks[0]["chunk_type"] == "definition"
    sections = repo.list_active_sections("doc-1")
    assert sections[0]["id"] == "section-1"


def test_sqlite_init_migrates_legacy_chunk_table_before_section_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE document_chunks (
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
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """
        )

    repo = SQLiteRepo(db_path)
    repo.init_db()

    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(document_chunks)").fetchall()
        }
        indexes = {
            row[1]
            for row in conn.execute("PRAGMA index_list(document_chunks)").fetchall()
        }

    assert "section_id" in columns
    assert "heading" in columns
    assert "idx_chunks_section_active" in indexes
