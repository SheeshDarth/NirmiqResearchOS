import re
import unicodedata


_OCR_REPLACEMENTS = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\u019f": "ti",
    "\u019e": "n",
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00e2\u20ac\u2122": "'",
    "\u00ef\u00ac\u20ac": "ff",
    "\u00ef\u00ac\u0081": "fi",
    "\u00ef\u00ac\u201a": "fl",
}


def normalize_ocr_text(text: str) -> str:
    """Normalize common PDF/OCR glyphs without changing meaning."""
    normalized = unicodedata.normalize("NFKC", text)
    for needle, replacement in _OCR_REPLACEMENTS.items():
        normalized = normalized.replace(needle, replacement)
    return normalized


def normalize_token_text(text: str) -> str:
    normalized = normalize_ocr_text(text).lower()
    normalized = re.sub(r"[^a-z0-9+.#-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()
