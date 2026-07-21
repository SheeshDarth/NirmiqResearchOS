from pathlib import Path

from app.adapters.retrieval.bm25_index import BM25Index
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.domain.retrieval_policy import RetrievalPolicy
from app.services.retrieval_service import RetrievalService


def test_selected_document_rows_are_reused_until_manifest_changes(tmp_path: Path) -> None:
    repo = SQLiteRepo(tmp_path / "nirmiq.db")
    repo.init_db()
    repo.insert_document(
        document_id="doc-1",
        source_path=str(tmp_path / "source.pdf"),
        content_hash="hash-v1",
        title="Source",
        mime_type="application/pdf",
        status="indexed",
    )
    repo.insert_document_section(
        section_id="sec-1",
        document_id="doc-1",
        index_version=1,
        section_index=0,
        heading="Chapter 1",
        section_path="Chapter 1",
        page_start=1,
        page_end=1,
        key_terms_json="[]",
    )
    repo.insert_document_chunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        index_version=1,
        chunk_index=0,
        page_start=1,
        page_end=1,
        text="Gaussian mixtures use several Gaussian distributions.",
        token_count=6,
        chunk_hash="chunk-hash-v1",
        section_id="sec-1",
        heading="Chapter 1",
        section_path="Chapter 1",
        chunk_type="definition",
        key_terms_json="[]",
    )
    service = RetrievalService(
        settings=object(),  # type: ignore[arg-type]
        policy=RetrievalPolicy(),
        sqlite_repo=repo,
        bm25_index=BM25Index(),
        reranker=object(),  # type: ignore[arg-type]
        embedder=object(),  # type: ignore[arg-type]
        chroma_repo=object(),  # type: ignore[arg-type]
    )

    first_chunks, first_sections, first_hit = service._load_active_document_rows("doc-1")
    second_chunks, second_sections, second_hit = service._load_active_document_rows("doc-1")

    assert first_hit is False
    assert second_hit is True
    assert second_chunks is first_chunks
    assert second_sections is first_sections

    repo.update_document_metadata(
        document_id="doc-1",
        content_hash="hash-v2",
        title="Source",
        mime_type="application/pdf",
    )

    _, _, third_hit = service._load_active_document_rows("doc-1")

    assert third_hit is False
    assert service._active_document_cache_stats()["cache_hits"] == 1
    assert service._active_document_cache_stats()["cache_misses"] == 2
