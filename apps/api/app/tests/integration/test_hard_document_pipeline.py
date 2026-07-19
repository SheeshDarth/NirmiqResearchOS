from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.parsing.pymupdf_parser import PyMuPDFParser
from app.adapters.parsing.tesseract_ocr import TesseractOCR
from app.main import app
from scripts.generate_hard_document_fixtures import generate_fixtures


def _ocr_available() -> bool:
    return TesseractOCR().is_available()


def test_hard_document_fixtures_are_byte_stable(tmp_path: Path) -> None:
    first = generate_fixtures(tmp_path / "first")
    second = generate_fixtures(tmp_path / "second")

    assert first["sha256"] == second["sha256"]


@pytest.mark.skipif(not _ocr_available(), reason="Tesseract OCR is not installed")
def test_hard_document_ingestion_query_and_diagram_roundtrip(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "hard-documents"
    generate_fixtures(fixture_dir)
    textbook = fixture_dir / "nirmiq_hard_textbook.pdf"
    scan = fixture_dir / "nirmiq_scanned_notes.pdf"
    handwriting = fixture_dir / "nirmiq_handwritten_note.png"

    parser = PyMuPDFParser()
    digital_pages = __import__("asyncio").run(parser.parse_pages(str(textbook)))
    digital_text = " ".join(text for _, text in digital_pages)
    assert "stability margin is calculated" in digital_text.lower()
    assert "recalibrate immediately" in digital_text.lower()

    with TestClient(app) as client:
        document_ids: dict[str, str] = {}
        for label, source in (
            ("textbook", textbook),
            ("scan", scan),
            ("handwriting", handwriting),
        ):
            response = client.post(
                "/ingest",
                json={"source_path": str(source), "title": f"Hard document {label}"},
            )
            assert response.status_code == 200, response.text
            document_ids[label] = response.json()["document_id"]

        scan_query = client.post(
            "/query",
            json={
                "session_id": "hard-doc-scan",
                "document_id": document_ids["scan"],
                "query": "What is spectral leakage?",
                "retrieval_mode": "bm25",
            },
        )
        assert scan_query.status_code == 200
        scan_body = scan_query.json()
        assert scan_body["grounded"] is True
        assert "frequency bins" in scan_body["answer"].lower()
        assert scan_body["citations"]

        handwriting_query = client.post(
            "/query",
            json={
                "session_id": "hard-doc-handwriting",
                "document_id": document_ids["handwriting"],
                "query": "What should happen before measuring thermal response?",
                "retrieval_mode": "bm25",
            },
        )
        assert handwriting_query.status_code == 200
        handwriting_body = handwriting_query.json()
        assert handwriting_body["grounded"] is True
        assert "zero the probe" in handwriting_body["answer"].lower()

        diagram_response = client.post(
            "/exam/diagrams/extract",
            json={"document_id": document_ids["textbook"], "force": True},
        )
        assert diagram_response.status_code == 200
        diagram_body = diagram_response.json()
        assert diagram_body["extracted_count"] >= 1
        assert any(asset["page_number"] == 4 for asset in diagram_body["assets"])
