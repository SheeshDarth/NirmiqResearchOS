import asyncio
from pathlib import Path

from app.adapters.parsing.pymupdf_parser import PyMuPDFParser


def test_pdf_parse_cache_reuses_content_hash(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF local cache smoke")
    parser = PyMuPDFParser(cache_root=tmp_path / "cache")
    calls = 0

    async def fake_parse_pdf(source_path: str) -> list[tuple[int, str]]:
        nonlocal calls
        calls += 1
        assert source_path == str(source)
        return [(1, "Cached local PDF text.")]

    parser._parse_pdf = fake_parse_pdf  # type: ignore[method-assign]

    first = asyncio.run(parser.parse_pages(str(source)))
    second = asyncio.run(parser.parse_pages(str(source)))

    assert first == [(1, "Cached local PDF text.")]
    assert second == first
    assert calls == 1
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1
