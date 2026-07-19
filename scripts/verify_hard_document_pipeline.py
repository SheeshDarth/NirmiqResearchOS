from __future__ import annotations

# ruff: noqa: E402

import argparse
import asyncio
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = WORKSPACE_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.adapters.parsing.tesseract_ocr import TesseractOCR
from app.core.config import get_settings
from app.core.deps import AppContainer


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _contains(text: str, phrase: str) -> bool:
    return _normalized(phrase) in _normalized(text)


async def verify(*, fixture_dir: Path, metrics_path: Path, report_path: Path) -> dict[str, object]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    result = metrics["results"]["bm25"]
    quality = result.get("answer_quality_metrics") or {}

    ocr = TesseractOCR()
    if not ocr.is_available():
        raise RuntimeError("Tesseract OCR is not available; hard-document verification cannot continue.")

    import pytesseract

    tesseract_version = str(pytesseract.get_tesseract_version()).splitlines()[0]
    tesseract_languages = sorted(pytesseract.get_languages(config=""))

    scan = fixture_dir / "nirmiq_scanned_notes.pdf"
    handwriting = fixture_dir / "nirmiq_handwritten_note.png"
    scan_page_1 = await ocr.extract_page(str(scan), 1)
    scan_page_2 = await ocr.extract_page(str(scan), 2)
    handwritten_text = await ocr.extract_page(str(handwriting), 1)

    checks = {
        "scan_definition_ocr": _contains(
            scan_page_1,
            "spectral leakage spreads energy into neighboring frequency bins",
        ),
        "scan_procedure_ocr": _contains(
            scan_page_2,
            "remove sensor bias then collect three reference readings",
        ),
        "handwriting_preparation_ocr": _contains(
            handwritten_text,
            "zero the probe and wait two minutes",
        ),
        "handwriting_correction_ocr": _contains(
            handwritten_text,
            "reduce controller gain before repeating the test",
        ),
    }

    settings = get_settings()
    container = AppContainer.from_settings(settings)
    container.sqlite_repo.init_db()

    textbook_path = str((fixture_dir / "nirmiq_hard_textbook.pdf").resolve())
    scan_path = str(scan.resolve())
    handwriting_path = str(handwriting.resolve())
    textbook_row = container.sqlite_repo.get_document_by_source_path(textbook_path)
    scan_row = container.sqlite_repo.get_document_by_source_path(scan_path)
    handwriting_row = container.sqlite_repo.get_document_by_source_path(handwriting_path)
    if not textbook_row or not scan_row or not handwriting_row:
        raise RuntimeError("One or more hard-document fixtures were not indexed by the evaluator.")

    textbook_chunks = container.sqlite_repo.list_active_chunks(str(textbook_row["id"]))
    scan_chunks = container.sqlite_repo.list_active_chunks(str(scan_row["id"]))
    handwriting_chunks = container.sqlite_repo.list_active_chunks(str(handwriting_row["id"]))
    textbook_text = " ".join(str(row.get("text") or "") for row in textbook_chunks)
    scan_text = " ".join(str(row.get("text") or "") for row in scan_chunks)
    handwriting_index_text = " ".join(str(row.get("text") or "") for row in handwriting_chunks)

    checks.update(
        {
            "equation_indexed": _contains(
                textbook_text,
                "stability margin is calculated as m target measured max abs target epsilon",
            ),
            "table_bands_indexed": _contains(textbook_text, "recalibrate immediately"),
            "scan_text_indexed": _contains(scan_text, "spectral leakage spreads energy"),
            "handwriting_text_indexed": _contains(handwriting_index_text, "zero the probe"),
        }
    )

    diagram_result = await container.exam_service.extract_diagrams(
        document_id=str(textbook_row["id"]),
        force=True,
    )
    checks["embedded_diagram_extracted"] = diagram_result.extracted_count >= 1

    checks.update(
        {
            "recall_at_8_gate": float(result.get("recall@8") or 0.0) >= 0.95,
            "citation_coverage_gate": float(result.get("citation_expected_coverage") or 0.0) >= 0.95,
            "answer_quality_gate": float(quality.get("pass_rate") or 0.0) >= 0.88,
            "answerability_gate": float(quality.get("answerability_correct") or 0.0) >= 1.0,
        }
    )

    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "version": "hard-documents-v1",
        "status": "passed" if not failed else "failed",
        "checks": checks,
        "failed_checks": failed,
        "fixture_counts": {
            "textbook_chunks": len(textbook_chunks),
            "scan_chunks": len(scan_chunks),
            "handwriting_chunks": len(handwriting_chunks),
            "extracted_diagrams": diagram_result.extracted_count,
        },
        "metrics": {
            "samples": result.get("samples"),
            "mrr": result.get("mrr"),
            "recall@3": result.get("recall@3"),
            "recall@8": result.get("recall@8"),
            "citation_expected_coverage": result.get("citation_expected_coverage"),
            "answer_quality_pass": quality.get("pass_rate"),
            "faithfulness": quality.get("faithfulness"),
            "answerability_correct": quality.get("answerability_correct"),
        },
        "runtime": {
            "offline": True,
            "retrieval_mode": "bm25",
            "ocr_engine": "tesseract",
            "python": platform.python_version(),
            "pymupdf": version("PyMuPDF"),
            "pillow": version("Pillow"),
            "pytesseract": version("pytesseract"),
            "tesseract": tesseract_version,
            "tesseract_languages": tesseract_languages,
        },
        "fixture_sha256": manifest.get("sha256", {}),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failed:
        raise RuntimeError(f"Hard-document verification failed: {', '.join(failed)}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify NIRMIQ hard-document ingestion and evaluation.")
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(
        verify(
            fixture_dir=args.fixture_dir.resolve(),
            metrics_path=args.metrics.resolve(),
            report_path=args.report.resolve(),
        )
    )


if __name__ == "__main__":
    main()
