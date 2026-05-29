from pathlib import Path


class PyMuPDFParser:
    """
    Local document parser.

    PDFs must use PyMuPDF so we never index raw binary PDF bytes as text.
    Plain text files still use the lightweight local reader.
    """

    async def parse_pages(self, source_path: str) -> list[tuple[int, str]]:
        path = Path(source_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            pages = await self._parse_pdf(source_path)
            return pages
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            # Force OCR fallback path in indexing service.
            return [(1, "")]
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [(1, text)]

    async def _parse_pdf(self, source_path: str) -> list[tuple[int, str]]:
        try:
            import fitz  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "PDF parsing requires PyMuPDF. Install it with "
                'python -m pip install "PyMuPDF>=1.26.0".'
            ) from exc
        pages: list[tuple[int, str]] = []
        document = fitz.open(source_path)
        try:
            for page_idx, page in enumerate(document, start=1):
                pages.append((page_idx, page.get_text("text")))
        finally:
            document.close()
        return pages
