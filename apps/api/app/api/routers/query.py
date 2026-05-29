from fastapi import APIRouter, Depends

from app.api.schemas.query import QueryRequest, QueryResponse
from app.core.deps import get_query_service
from app.services.query_service import QueryService

router = APIRouter()


@router.post("", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    return await service.run(payload)

