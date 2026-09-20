"""/search/ route — thin: validate the query, then delegate to SearchService."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_search_service
from app.api.schemas.search import SearchRequest, SearchResponse
from app.core.exceptions import BadRequestError
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/search/", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    query = payload.query.strip()
    if not query:
        raise BadRequestError("Query cannot be empty.")
    results = await service.search(query, payload.top_k)
    return SearchResponse(results=results)
