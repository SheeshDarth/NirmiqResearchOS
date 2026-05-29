import re
from pathlib import Path
from uuid import uuid4

from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.exam import (
    DiagramAssetItem,
    DiagramExtractionResponse,
    ExamProfileItem,
    ExamProfileRequest,
    QuestionBankImportResponse,
    QuestionBankItem,
)


class ExamService:
    def __init__(self, sqlite_repo: SQLiteRepo, workspace_root: Path) -> None:
        self._sqlite_repo = sqlite_repo
        self._workspace_root = workspace_root
        self._diagram_root = workspace_root / "data" / "processed" / "diagrams"

    async def upsert_profile(self, payload: ExamProfileRequest) -> ExamProfileItem:
        self._require_document(payload.document_id)
        row = self._sqlite_repo.upsert_exam_profile(
            profile_id=str(uuid4()),
            session_id=payload.session_id,
            document_id=payload.document_id,
            title=payload.title,
            marks=payload.marks,
            answer_style=payload.answer_style,
            content_type=payload.content_type,
            instructions=payload.instructions,
        )
        return self._profile_item(row)

    async def list_profiles(self, session_id: str | None = None) -> list[ExamProfileItem]:
        rows = self._sqlite_repo.list_exam_profiles(session_id=session_id)
        return [self._profile_item(row) for row in rows]

    async def import_question_bank(self, document_id: str, raw_text: str) -> QuestionBankImportResponse:
        self._require_document(document_id)
        parsed = self._parse_questions(raw_text)
        self._sqlite_repo.replace_question_bank_items(
            document_id=document_id,
            items=[
                {
                    "id": str(uuid4()),
                    "question": question,
                    "marks": marks,
                    "source_label": "manual-import",
                    "page_start": None,
                    "page_end": None,
                }
                for question, marks in parsed
            ],
        )
        rows = self._sqlite_repo.list_question_bank_items(document_id=document_id)
        return QuestionBankImportResponse(
            document_id=document_id,
            imported_count=len(rows),
            items=[self._question_item(row) for row in rows],
        )

    async def list_question_bank(self, document_id: str) -> list[QuestionBankItem]:
        self._require_document(document_id)
        rows = self._sqlite_repo.list_question_bank_items(document_id=document_id)
        return [self._question_item(row) for row in rows]

    async def extract_diagrams(self, document_id: str, force: bool = False) -> DiagramExtractionResponse:
        document = self._require_document(document_id)
        source_path = Path(str(document["source_path"]))
        if source_path.suffix.lower() != ".pdf":
            return DiagramExtractionResponse(document_id=document_id, extracted_count=0, assets=[])

        existing = self._sqlite_repo.list_diagram_assets(document_id=document_id)
        if existing and not force:
            return DiagramExtractionResponse(
                document_id=document_id,
                extracted_count=len(existing),
                assets=[self._diagram_item(row) for row in existing],
            )

        if force:
            self._sqlite_repo.delete_diagram_assets(document_id=document_id)

        try:
            import fitz  # type: ignore
        except Exception as exc:
            raise RuntimeError("Diagram extraction requires PyMuPDF.") from exc

        target_dir = self._diagram_root / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        inserted: list[dict[str, object]] = []
        pdf = fitz.open(str(source_path))
        try:
            for page_index, page in enumerate(pdf, start=1):
                for image_index, image in enumerate(page.get_images(full=True), start=1):
                    xref = image[0]
                    extracted = pdf.extract_image(xref)
                    image_bytes = extracted.get("image")
                    if not image_bytes:
                        continue
                    extension = str(extracted.get("ext") or "png").lower()
                    image_path = target_dir / f"page_{page_index:04d}_image_{image_index:02d}.{extension}"
                    image_path.write_bytes(image_bytes)
                    row = self._sqlite_repo.insert_diagram_asset(
                        asset_id=str(uuid4()),
                        document_id=document_id,
                        page_number=page_index,
                        image_index=image_index,
                        image_path=str(image_path),
                        width=int(extracted.get("width") or 0) or None,
                        height=int(extracted.get("height") or 0) or None,
                        caption=self._nearby_caption(page.get_text("text")),
                    )
                    inserted.append(row)
        finally:
            pdf.close()

        rows = self._sqlite_repo.list_diagram_assets(document_id=document_id)
        return DiagramExtractionResponse(
            document_id=document_id,
            extracted_count=len(rows),
            assets=[self._diagram_item(row) for row in rows],
        )

    async def list_diagrams(self, document_id: str) -> list[DiagramAssetItem]:
        self._require_document(document_id)
        rows = self._sqlite_repo.list_diagram_assets(document_id=document_id)
        return [self._diagram_item(row) for row in rows]

    def _require_document(self, document_id: str) -> dict[str, object]:
        document = self._sqlite_repo.get_document_by_id(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        return document

    @staticmethod
    def _parse_questions(raw_text: str) -> list[tuple[str, int | None]]:
        questions: list[tuple[str, int | None]] = []
        for line in raw_text.splitlines():
            cleaned = re.sub(r"^\s*(?:\d+[\).:-]?|[-*])\s*", "", line).strip()
            if not cleaned:
                continue
            marks_match = re.search(r"(?:\(|\[)?\s*(\d{1,2})\s*(?:marks?|m)\s*(?:\)|\])?", cleaned, re.I)
            marks = int(marks_match.group(1)) if marks_match else None
            cleaned = re.sub(r"(?:\(|\[)?\s*\d{1,2}\s*(?:marks?|m)\s*(?:\)|\])?", "", cleaned, flags=re.I).strip(" -")
            lower = cleaned.lower()
            looks_like_question = cleaned.endswith("?") or lower.startswith(
                ("explain", "define", "describe", "compare", "discuss", "write", "what", "why", "how")
            )
            if looks_like_question:
                questions.append((cleaned, marks))
        return questions[:200]

    @staticmethod
    def _nearby_caption(page_text: str) -> str | None:
        for line in page_text.splitlines():
            stripped = line.strip()
            if re.match(r"^(figure|fig\.|diagram|table)\s+\d+", stripped, re.I):
                return stripped[:240]
        return None

    @staticmethod
    def _profile_item(row: dict[str, object]) -> ExamProfileItem:
        return ExamProfileItem(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            document_id=str(row["document_id"]),
            title=str(row["title"]),
            marks=int(row["marks"]),
            answer_style=str(row["answer_style"]),
            content_type=str(row["content_type"]),
            instructions=str(row["instructions"]) if row.get("instructions") is not None else None,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _question_item(row: dict[str, object]) -> QuestionBankItem:
        return QuestionBankItem(
            id=str(row["id"]),
            document_id=str(row["document_id"]),
            question=str(row["question"]),
            marks=int(row["marks"]) if row.get("marks") is not None else None,
            source_label=str(row["source_label"]) if row.get("source_label") is not None else None,
            page_start=int(row["page_start"]) if row.get("page_start") is not None else None,
            page_end=int(row["page_end"]) if row.get("page_end") is not None else None,
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _diagram_item(row: dict[str, object]) -> DiagramAssetItem:
        return DiagramAssetItem(
            id=str(row["id"]),
            document_id=str(row["document_id"]),
            page_number=int(row["page_number"]),
            image_index=int(row["image_index"]),
            image_path=str(row["image_path"]),
            width=int(row["width"]) if row.get("width") is not None else None,
            height=int(row["height"]) if row.get("height") is not None else None,
            caption=str(row["caption"]) if row.get("caption") is not None else None,
            created_at=str(row["created_at"]),
        )
