import hashlib
import json
import re
from dataclasses import dataclass

from app.adapters.llm.embedder import Embedder
from app.adapters.parsing.pymupdf_parser import PyMuPDFParser
from app.adapters.parsing.tesseract_ocr import TesseractOCR
from app.adapters.storage.chroma_repo import ChromaRepo
from app.adapters.storage.sqlite_repo import SQLiteRepo


@dataclass(slots=True)
class ChunkDraft:
    chunk_index: int
    page_start: int
    page_end: int
    text: str
    section_index: int
    heading: str
    section_path: str
    chunk_type: str
    key_terms: list[str]


@dataclass(slots=True)
class SectionDraft:
    section_index: int
    heading: str
    section_path: str
    page_start: int
    page_end: int
    text: str
    key_terms: list[str]


class IndexingService:
    def __init__(
        self,
        sqlite_repo: SQLiteRepo,
        parser: PyMuPDFParser,
        ocr: TesseractOCR,
        embedder: Embedder,
        chroma_repo: ChromaRepo,
    ) -> None:
        self._sqlite_repo = sqlite_repo
        self._parser = parser
        self._ocr = ocr
        self._embedder = embedder
        self._chroma_repo = chroma_repo
        self._chunk_tokens = 180
        self._chunk_overlap = 30
        self._min_page_text_chars = 80
        self._ocr_applied_pages: set[int] = set()

    async def index_document(self, document_id: str) -> None:
        document = self._sqlite_repo.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        source_path = str(document["source_path"])
        pages = await self._parser.parse_pages(source_path)
        pages = await self._apply_ocr_fallback(source_path=source_path, pages=pages)
        sections = self._section_pages(pages)
        chunks = self._chunk_sections(sections)
        if not chunks:
            raise ValueError(
                "No readable text could be extracted from this file. "
                "If this is a scanned PDF or image, install OCR support or upload a clearer source."
            )
        index_version = self._sqlite_repo.get_next_index_version(document_id)
        self._sqlite_repo.deactivate_document_chunks(document_id)
        self._sqlite_repo.deactivate_document_sections(document_id)

        section_ids: dict[int, str] = {}
        for section in sections:
            section_id = self._stable_section_id(
                document_id=document_id,
                index_version=index_version,
                section_index=section.section_index,
                heading=section.heading,
            )
            section_ids[section.section_index] = section_id
            self._sqlite_repo.insert_document_section(
                section_id=section_id,
                document_id=document_id,
                index_version=index_version,
                section_index=section.section_index,
                heading=section.heading,
                section_path=section.section_path,
                page_start=section.page_start,
                page_end=section.page_end,
                key_terms_json=json.dumps(section.key_terms),
            )

        chunk_rows: list[dict[str, object]] = []
        for chunk in chunks:
            chunk_id = self._stable_chunk_id(document_id, index_version, chunk.chunk_index, chunk.text)
            quality_score = self._chunk_quality_score(chunk.text)
            section_id = section_ids.get(chunk.section_index)
            self._sqlite_repo.insert_document_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                index_version=index_version,
                chunk_index=chunk.chunk_index,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
                token_count=len(chunk.text.split()),
                chunk_hash=self._hash_text(chunk.text),
                quality_score=quality_score,
                section_id=section_id,
                heading=chunk.heading,
                section_path=chunk.section_path,
                chunk_type=chunk.chunk_type,
                key_terms_json=json.dumps(chunk.key_terms),
            )
            chunk_rows.append(
                {
                    "id": chunk_id,
                    "document_id": document_id,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "text": chunk.text,
                    "quality_score": quality_score,
                    "section_id": section_id,
                    "heading": chunk.heading,
                    "section_path": chunk.section_path,
                    "chunk_type": chunk.chunk_type,
                    "key_terms_json": json.dumps(chunk.key_terms),
                }
            )
        await self._chroma_repo.delete_document(document_id)
        if chunk_rows and self._chroma_repo.is_available():
            embeddings = await self._embedder.embed([str(row["text"]) for row in chunk_rows])
            await self._chroma_repo.upsert_chunks(chunks=chunk_rows, embeddings=embeddings)
        self._sqlite_repo.mark_document_status(document_id=document_id, status="indexed")

    async def _apply_ocr_fallback(
        self, source_path: str, pages: list[tuple[int, str]]
    ) -> list[tuple[int, str]]:
        self._ocr_applied_pages = set()
        if not pages or not self._ocr.is_available():
            return pages
        enriched: list[tuple[int, str]] = []
        for page_number, page_text in pages:
            normalized = self._normalize_text(page_text)
            if len(normalized) >= self._min_page_text_chars:
                enriched.append((page_number, page_text))
                continue
            ocr_text = await self._ocr.extract_page(source_path=source_path, page_number=page_number)
            ocr_normalized = self._normalize_text(ocr_text)
            if len(ocr_normalized) > len(normalized):
                self._ocr_applied_pages.add(page_number)
                enriched.append((page_number, ocr_text))
            else:
                enriched.append((page_number, page_text))
        return enriched

    def _section_pages(self, pages: list[tuple[int, str]]) -> list[SectionDraft]:
        sections: list[SectionDraft] = []
        current_heading = "Document"
        current_start_page: int | None = None
        current_end_page: int | None = None
        current_lines: list[str] = []

        def flush() -> None:
            nonlocal current_lines, current_heading, current_start_page, current_end_page
            normalized = self._normalize_text("\n".join(current_lines))
            if not normalized:
                current_lines = []
                return
            section_index = len(sections)
            sections.append(
                SectionDraft(
                    section_index=section_index,
                    heading=current_heading,
                    section_path=current_heading,
                    page_start=current_start_page or 1,
                    page_end=current_end_page or current_start_page or 1,
                    text=normalized,
                    key_terms=self._extract_key_terms(f"{current_heading} {normalized}"),
                )
            )
            current_lines = []

        for page_no, raw_text in pages:
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if not lines and raw_text.strip():
                lines = [raw_text.strip()]
            for line in lines:
                if self._looks_like_heading(line):
                    if current_lines:
                        flush()
                    current_heading = self._clean_heading(line)
                    current_start_page = page_no
                    current_end_page = page_no
                    current_lines = [current_heading]
                    continue
                if current_start_page is None:
                    current_start_page = page_no
                current_end_page = page_no
                current_lines.append(line)
        flush()

        if sections:
            return self._coalesce_ocr_fragments(sections)
        normalized_pages = [(page_no, self._normalize_text(text)) for page_no, text in pages if text.strip()]
        if not normalized_pages:
            return []
        text = " ".join(text for _, text in normalized_pages)
        return [
            SectionDraft(
                section_index=0,
                heading="Document",
                section_path="Document",
                page_start=normalized_pages[0][0],
                page_end=normalized_pages[-1][0],
                text=text,
                key_terms=self._extract_key_terms(text),
            )
        ]

    def _coalesce_ocr_fragments(self, sections: list[SectionDraft]) -> list[SectionDraft]:
        """Join short same-page OCR labels so retrieval sees complete evidence blocks.

        Scanned layouts often put every visual label on its own OCR line. The normal
        heading heuristic correctly recognizes those labels, but treating each one as
        an independent retrieval section creates tiny, low-context chunks. This repair
        is limited to pages where OCR replaced the parser output and never crosses a
        page boundary or the chunk token budget.
        """

        if not getattr(self, "_ocr_applied_pages", set()):
            return sections

        fragment_limit = 45
        merged: list[SectionDraft] = []
        for section in sections:
            if not merged:
                merged.append(section)
                continue

            previous = merged[-1]
            same_ocr_page = (
                previous.page_start == previous.page_end == section.page_start == section.page_end
                and section.page_start in self._ocr_applied_pages
            )
            previous_words = previous.text.split()
            current_words = section.text.split()
            combined_words = len(previous_words) + len(current_words)
            should_merge = (
                same_ocr_page
                and combined_words <= self._ocr_chunk_tokens()
                and (len(previous_words) < fragment_limit or len(current_words) < fragment_limit)
            )
            if not should_merge:
                merged.append(section)
                continue

            headings = [heading for heading in (previous.heading, section.heading) if heading]
            combined_heading = " / ".join(dict.fromkeys(headings))
            merged[-1] = SectionDraft(
                section_index=previous.section_index,
                heading=combined_heading[:180],
                section_path=combined_heading[:180],
                page_start=min(previous.page_start, section.page_start),
                page_end=max(previous.page_end, section.page_end),
                text=f"{previous.text} {section.text}".strip(),
                key_terms=list(dict.fromkeys(previous.key_terms + section.key_terms))[:12],
            )

        return [
            SectionDraft(
                section_index=index,
                heading=section.heading,
                section_path=section.section_path,
                page_start=section.page_start,
                page_end=section.page_end,
                text=section.text,
                key_terms=section.key_terms,
            )
            for index, section in enumerate(merged)
        ]

    def _ocr_chunk_tokens(self) -> int:
        """Use a wider bounded window for OCR pages whose labels are fragmented."""

        if getattr(self, "_ocr_applied_pages", set()):
            return max(self._chunk_tokens, min(self._chunk_tokens + 120, 320))
        return self._chunk_tokens

    def _chunk_sections(self, sections: list[SectionDraft]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        chunk_tokens = self._ocr_chunk_tokens()
        chunk_overlap = min(self._chunk_overlap + 30, chunk_tokens // 3)
        stride = max(chunk_tokens - chunk_overlap, 1)
        chunk_index = 0
        for section in sections:
            words = section.text.split()
            if not words:
                continue
            chunk_type = "definition" if self._looks_like_definition(section.text) else "body"
            for start in range(0, len(words), stride):
                window = words[start : start + chunk_tokens]
                if not window:
                    break
                chunk_text = " ".join(window)
                drafts.append(
                    ChunkDraft(
                        chunk_index=chunk_index,
                        page_start=section.page_start,
                        page_end=section.page_end,
                        text=chunk_text,
                        section_index=section.section_index,
                        heading=section.heading,
                        section_path=section.section_path,
                        chunk_type=chunk_type,
                        key_terms=section.key_terms,
                    )
                )
                chunk_index += 1
                if start + chunk_tokens >= len(words):
                    break
        return drafts

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        cleaned = re.sub(r"\s+", " ", line.strip())
        if not 4 <= len(cleaned) <= 90:
            return False
        words = cleaned.split()
        if len(words) > 12:
            return False
        if cleaned.endswith((".", ",", ";")):
            return False
        if re.match(r"^(chapter|section|part|unit|module|lesson|appendix)\b", cleaned, re.I):
            return True
        if re.match(r"^\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9 ,:()/-]+$", cleaned):
            return True
        alpha_chars = [char for char in cleaned if char.isalpha()]
        uppercase_ratio = (
            sum(1 for char in alpha_chars if char.isupper()) / max(len(alpha_chars), 1)
        )
        title_like_words = sum(1 for word in words if word[:1].isupper())
        return uppercase_ratio >= 0.72 or title_like_words >= max(2, len(words) - 1)

    @staticmethod
    def _clean_heading(line: str) -> str:
        return re.sub(r"\s+", " ", line.strip()).strip(":- ")

    @staticmethod
    def _looks_like_definition(text: str) -> bool:
        return bool(re.search(r"\b(is|are|refers to|defined as|means)\b", text[:500], re.I))

    @staticmethod
    def _extract_key_terms(text: str, limit: int = 12) -> list[str]:
        stopwords = {
            "about",
            "after",
            "also",
            "and",
            "are",
            "because",
            "been",
            "between",
            "chapter",
            "does",
            "from",
            "have",
            "into",
            "that",
            "the",
            "their",
            "these",
            "this",
            "through",
            "using",
            "with",
            "which",
            "will",
        }
        counts: dict[str, int] = {}
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text.lower()):
            if token in stopwords or len(token) < 4:
                continue
            counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [term for term, _ in ranked[:limit]]

    @staticmethod
    def _normalize_text(text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        return " ".join(line for line in lines if line)

    @staticmethod
    def _chunk_quality_score(text: str) -> float:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return 0.0
        chars = len(normalized)
        alpha = sum(1 for char in normalized if char.isalpha())
        digits = sum(1 for char in normalized if char.isdigit())
        replacement = normalized.count("\ufffd") + normalized.count("□") + normalized.count("�")
        symbols = sum(1 for char in normalized if not char.isalnum() and not char.isspace())
        words = normalized.split()
        unique_ratio = len({word.lower() for word in words}) / max(len(words), 1)
        alpha_ratio = alpha / max(chars, 1)
        symbol_ratio = symbols / max(chars, 1)
        digit_ratio = digits / max(chars, 1)
        short_penalty = 0.18 if len(words) < 35 else 0.0
        repeated_penalty = 0.18 if unique_ratio < 0.38 else 0.0
        reference_penalty = 0.18 if re.search(r"\b(references|bibliography)\b", normalized, re.I) else 0.0
        noise_penalty = min(0.38, replacement * 0.04 + max(0.0, symbol_ratio - 0.08) * 1.8)
        digit_penalty = min(0.18, max(0.0, digit_ratio - 0.16) * 0.8)
        alpha_bonus = min(0.16, max(0.0, alpha_ratio - 0.48) * 0.35)
        score = 0.78 + alpha_bonus - short_penalty - repeated_penalty - reference_penalty - noise_penalty - digit_penalty
        return round(min(1.0, max(0.12, score)), 3)

    @staticmethod
    def _stable_chunk_id(
        document_id: str, index_version: int, chunk_index: int, text: str
    ) -> str:
        digest = hashlib.sha1(
            f"{document_id}|{index_version}|{chunk_index}|{text}".encode("utf-8")
        ).hexdigest()
        return f"chk_{digest}"

    @staticmethod
    def _stable_section_id(
        document_id: str,
        index_version: int,
        section_index: int,
        heading: str,
    ) -> str:
        digest = hashlib.sha1(
            f"{document_id}|{index_version}|{section_index}|{heading}".encode("utf-8")
        ).hexdigest()
        return f"sec_{digest}"

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
