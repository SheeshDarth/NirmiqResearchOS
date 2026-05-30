from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.schemas.ingest import (
    IngestJobsResponse,
    IngestRequest,
    IngestResponse,
    IngestStatusResponse,
)
from app.core.deps import get_ingestion_service
from app.services.ingestion_service import IngestionService

router = APIRouter()


@router.post("", response_model=IngestResponse)
async def ingest_document(
    payload: IngestRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    try:
        return await service.ingest(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    force_reindex: bool = Form(False),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    try:
        content = await file.read()
        return await service.ingest_upload(
            filename=file.filename or "upload",
            content=content,
            content_type=file.content_type,
            title=title,
            force_reindex=force_reindex,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{document_id}", response_model=IngestStatusResponse)
async def get_ingest_status(
    document_id: str,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestStatusResponse:
    try:
        return await service.get_status(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{document_id}/jobs", response_model=IngestJobsResponse)
async def get_ingest_jobs(
    document_id: str,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestJobsResponse:
    try:
        return await service.get_jobs(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
