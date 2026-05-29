from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.exam import (
    DiagramAssetItem,
    DiagramExtractionRequest,
    DiagramExtractionResponse,
    ExamProfileItem,
    ExamProfileRequest,
    QuestionBankImportRequest,
    QuestionBankImportResponse,
    QuestionBankItem,
)
from app.core.deps import get_exam_service
from app.services.exam_service import ExamService

router = APIRouter()


@router.post("/profiles", response_model=ExamProfileItem)
async def upsert_exam_profile(
    payload: ExamProfileRequest,
    service: ExamService = Depends(get_exam_service),
) -> ExamProfileItem:
    try:
        return await service.upsert_profile(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/profiles", response_model=list[ExamProfileItem])
async def list_exam_profiles(
    session_id: str | None = Query(default=None),
    service: ExamService = Depends(get_exam_service),
) -> list[ExamProfileItem]:
    return await service.list_profiles(session_id=session_id)


@router.post("/question-bank/import", response_model=QuestionBankImportResponse)
async def import_question_bank(
    payload: QuestionBankImportRequest,
    service: ExamService = Depends(get_exam_service),
) -> QuestionBankImportResponse:
    try:
        return await service.import_question_bank(
            document_id=payload.document_id,
            raw_text=payload.raw_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/question-bank/{document_id}", response_model=list[QuestionBankItem])
async def list_question_bank(
    document_id: str,
    service: ExamService = Depends(get_exam_service),
) -> list[QuestionBankItem]:
    try:
        return await service.list_question_bank(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/diagrams/extract", response_model=DiagramExtractionResponse)
async def extract_diagrams(
    payload: DiagramExtractionRequest,
    service: ExamService = Depends(get_exam_service),
) -> DiagramExtractionResponse:
    try:
        return await service.extract_diagrams(document_id=payload.document_id, force=payload.force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/diagrams/{document_id}", response_model=list[DiagramAssetItem])
async def list_diagrams(
    document_id: str,
    service: ExamService = Depends(get_exam_service),
) -> list[DiagramAssetItem]:
    try:
        return await service.list_diagrams(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
