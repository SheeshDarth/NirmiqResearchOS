import hashlib
import json
from pathlib import Path


class PyMuPDFParser:
    """
    Local document parser.

    PDFs must use PyMuPDF so we never index raw binary PDF bytes as text.
    Plain text files still use the lightweight local reader.
    """

    _cache_version = 1

    def __init__(self, cache_root: Path | None = None) -> None:
        self._cache_root = cache_root

    async def parse_pages(self, source_path: str) -> list[tuple[int, str]]:
        path = Path(source_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            pages = await self._parse_pdf_with_cache(path)
            return pages
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            # Force OCR fallback path in indexing service.
            return [(1, "")]
        text = self._clean_text(path.read_text(encoding="utf-8", errors="ignore"))
        return [(1, text)]

    async def _parse_pdf_with_cache(self, path: Path) -> list[tuple[int, str]]:
        if not self._cache_root:
            return await self._parse_pdf(str(path))

        cache_key = self._hash_file(path)
        cache_path = self._cache_root / f"{cache_key}.v{self._cache_version}.json"
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached

        pages = await self._parse_pdf(str(path))
        self._write_cache(cache_path, pages)
        return pages

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
                pages.append((page_idx, self._clean_text(page.get_text("text"))))
        finally:
            document.close()
        return pages

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _read_cache(cache_path: Path) -> list[tuple[int, str]] | None:
        if not cache_path.exists():
            return None
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if payload.get("version") != PyMuPDFParser._cache_version:
            return None
        pages = payload.get("pages")
        if not isinstance(pages, list):
            return None
        parsed: list[tuple[int, str]] = []
        for item in pages:
            if not isinstance(item, dict):
                return None
            page_number = item.get("page_number")
            text = item.get("text")
            if not isinstance(page_number, int) or not isinstance(text, str):
                return None
            parsed.append((page_number, text))
        return parsed

    @staticmethod
    def _write_cache(cache_path: Path, pages: list[tuple[int, str]]) -> None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(
                    {
                        "version": PyMuPDFParser._cache_version,
                        "pages": [
                            {"page_number": page_number, "text": text}
                            for page_number, text in pages
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            # Parsing must remain reliable even when the cache directory is unavailable.
            return

    @staticmethod
    def _clean_text(text: str) -> str:
        replacements = {
            "â¢": "-",
            "â": "-",
            "â": "-",
            "â": "*",
            "â": "in",
            "â¤": "<=",
            "â¥": ">=",
            "â": "~",
            "ï¬": "fi",
            "ï¬": "fl",
        }
        cleaned = text
        for bad, good in replacements.items():
            cleaned = cleaned.replace(bad, good)
        return cleaned
