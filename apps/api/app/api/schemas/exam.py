from pydantic import BaseModel, Field


class ExamProfileRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    title: str = "Default Exam Profile"
    marks: int = Field(default=10, ge=1, le=100)
    answer_style: str = "exam-ready"
    content_type: str = "conceptual"
    instructions: str | None = None


class ExamProfileItem(BaseModel):
    id: str
    session_id: str
    document_id: str
    title: str
    marks: int
    answer_style: str
    content_type: str
    instructions: str | None = None
    created_at: str
    updated_at: str


class QuestionBankImportRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    raw_text: str = Field(..., min_length=1)


class QuestionBankItem(BaseModel):
    id: str
    document_id: str
    question: str
    marks: int | None = None
    source_label: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    created_at: str


class QuestionBankImportResponse(BaseModel):
    document_id: str
    imported_count: int
    items: list[QuestionBankItem]


class DiagramExtractionRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    force: bool = False


class DiagramAssetItem(BaseModel):
    id: str
    document_id: str
    page_number: int
    image_index: int
    image_path: str
    width: int | None = None
    height: int | None = None
    caption: str | None = None
    created_at: str


class DiagramExtractionResponse(BaseModel):
    document_id: str
    extracted_count: int
    assets: list[DiagramAssetItem]
