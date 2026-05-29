from __future__ import annotations

from io import BytesIO
from pathlib import Path


class TesseractOCR:
    """Optional OCR adapter with graceful fallback when deps are unavailable."""

    def __init__(self) -> None:
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import pytesseract  # type: ignore  # noqa: F401
            from PIL import Image  # type: ignore  # noqa: F401
        except Exception:
            self._available = False
            return False
        self._available = True
        return True

    async def extract_page(self, source_path: str, page_number: int = 1) -> str:
        path = Path(source_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return await self._extract_pdf_page(source_path=source_path, page_number=page_number)
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            return await self._extract_image(source_path)
        return ""

    async def _extract_pdf_page(self, source_path: str, page_number: int) -> str:
        if not self.is_available():
            return ""
        try:
            import fitz  # type: ignore
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception:
            return ""

        document = fitz.open(source_path)
        try:
            idx = max(page_number - 1, 0)
            if idx >= len(document):
                return ""
            page = document[idx]
            pix = page.get_pixmap(dpi=220)
            image_bytes = pix.tobytes("png")
            image = Image.open(BytesIO(image_bytes))
            return str(pytesseract.image_to_string(image)).strip()
        except Exception:
            return ""
        finally:
            document.close()

    async def _extract_image(self, source_path: str) -> str:
        if not self.is_available():
            return ""
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception:
            return ""
        try:
            image = Image.open(source_path)
            return str(pytesseract.image_to_string(image)).strip()
        except Exception:
            return ""
