from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.documents import DocumentDeleteResponse, DocumentDetailResponse, DocumentListResponse
from app.core.deps import get_documents_service
from app.services.documents_service import DocumentsService

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentListResponse:
    return await service.list_documents()


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentDetailResponse:
    try:
        return await service.get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentDeleteResponse:
    try:
        return await service.delete_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
