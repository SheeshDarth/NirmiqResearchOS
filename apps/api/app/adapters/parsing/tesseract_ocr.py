from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import shutil


class TesseractOCR:
    """Optional OCR adapter with graceful fallback when deps are unavailable."""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        self._available: bool | None = None
        self._executable_path = str(executable_path) if executable_path else None
        self._resolved_command: str | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore  # noqa: F401
        except Exception:
            self._available = False
            return False

        command = self._resolve_executable(self._executable_path)
        if not command:
            self._available = False
            return False
        pytesseract.pytesseract.tesseract_cmd = command
        self._resolved_command = command
        self._available = self._probe_executable(command)
        return self._available

    @staticmethod
    def _resolve_executable(explicit_path: str | None = None) -> str | None:
        candidates: list[str] = []
        if explicit_path:
            candidates.append(explicit_path)
        configured = os.getenv("TESSERACT_CMD", "").strip()
        if configured:
            candidates.append(configured)
        path_command = shutil.which("tesseract")
        if path_command:
            candidates.append(path_command)

        for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            root = os.getenv(env_name, "").strip()
            if not root:
                continue
            if env_name == "LOCALAPPDATA":
                candidates.append(str(Path(root) / "Programs" / "Tesseract-OCR" / "tesseract.exe"))
            else:
                candidates.append(str(Path(root) / "Tesseract-OCR" / "tesseract.exe"))

        seen: set[str] = set()
        for candidate in candidates:
            path = Path(candidate).expanduser()
            normalized = str(path.resolve(strict=False))
            if normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            if path.is_file():
                return normalized
        return None

    @staticmethod
    def _probe_executable(command: str) -> bool:
        try:
            import pytesseract  # type: ignore

            pytesseract.pytesseract.tesseract_cmd = command
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def _page_config() -> str:
        """Allow local installs to select a layout mode for multi-column scans."""

        raw_psm = os.getenv("TESSERACT_PSM", "3").strip()
        psm = raw_psm if raw_psm.isdigit() and 0 <= int(raw_psm) <= 13 else "3"
        return f"--psm {psm}"

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
            return str(pytesseract.image_to_string(image, config=self._page_config())).strip()
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
            return str(pytesseract.image_to_string(image, config=self._page_config())).strip()
        except Exception:
            return ""
