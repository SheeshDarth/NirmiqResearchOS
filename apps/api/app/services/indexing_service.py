import hashlib
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

    async def index_document(self, document_id: str) -> None:
        document = self._sqlite_repo.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        source_path = str(document["source_path"])
        pages = await self._parser.parse_pages(source_path)
        pages = await self._apply_ocr_fallback(source_path=source_path, pages=pages)
        chunks = self._chunk_pages(pages)
        index_version = self._sqlite_repo.get_next_index_version(document_id)
        self._sqlite_repo.deactivate_document_chunks(document_id)

        chunk_rows: list[dict[str, object]] = []
        for chunk in chunks:
            chunk_id = self._stable_chunk_id(document_id, index_version, chunk.chunk_index, chunk.text)
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
            )
            chunk_rows.append(
                {
                    "id": chunk_id,
                    "document_id": document_id,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "text": chunk.text,
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
                enriched.append((page_number, ocr_text))
            else:
                enriched.append((page_number, page_text))
        return enriched

    def _chunk_pages(self, pages: list[tuple[int, str]]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        normalized_pages = [(page_no, self._normalize_text(text)) for page_no, text in pages if text.strip()]
        if not normalized_pages:
            return drafts

        words: list[tuple[int, str]] = []
        for page_no, text in normalized_pages:
            for token in text.split():
                words.append((page_no, token))

        if not words:
            return drafts

        stride = max(self._chunk_tokens - self._chunk_overlap, 1)
        chunk_index = 0
        for start in range(0, len(words), stride):
            window = words[start : start + self._chunk_tokens]
            if not window:
                break
            page_start = window[0][0]
            page_end = window[-1][0]
            chunk_text = " ".join(word for _, word in window)
            drafts.append(
                ChunkDraft(
                    chunk_index=chunk_index,
                    page_start=page_start,
                    page_end=page_end,
                    text=chunk_text,
                )
            )
            chunk_index += 1
            if start + self._chunk_tokens >= len(words):
                break
        return drafts

    @staticmethod
    def _normalize_text(text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        return " ".join(line for line in lines if line)

    @staticmethod
    def _stable_chunk_id(
        document_id: str, index_version: int, chunk_index: int, text: str
    ) -> str:
        digest = hashlib.sha1(
            f"{document_id}|{index_version}|{chunk_index}|{text}".encode("utf-8")
        ).hexdigest()
        return f"chk_{digest}"

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
