from app.services.indexing_service import IndexingService


def test_chunk_quality_scores_clean_academic_text_high() -> None:
    clean = (
        "Retrieval augmented generation combines a search component with grounded synthesis. "
        "The system uses cited evidence from source documents to reduce hallucination and improve trust. "
        "A useful academic assistant should preserve source context, explain limitations, and avoid unsupported claims."
    )

    assert IndexingService._chunk_quality_score(clean) >= 0.78


def test_chunk_quality_penalizes_noisy_pdf_text() -> None:
    noisy = "%PDF-1.4 □□□ 000 111 !!! !!! !!! KZ`?Ah3o_NDçkD5□□□ <EOS> <pad> □□□"

    assert IndexingService._chunk_quality_score(noisy) < 0.7
