from __future__ import annotations

from fastapi import APIRouter, Query

from api.dependencies import DB
from api.schemas.responses import SearchHit
from api.services import search_service as svc

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchHit])
async def search(
    session: DB,
    q:       str = Query(..., min_length=1, max_length=100),
    limit:   int = Query(10, ge=1, le=50),
) -> list[SearchHit]:
    return await svc.search(session, q, limit)


@router.get("/autocomplete", response_model=list[SearchHit])
async def autocomplete(
    session: DB,
    q:       str = Query(..., min_length=1, max_length=100),
    limit:   int = Query(10, ge=1, le=50),
) -> list[SearchHit]:
    return await svc.autocomplete(session, q, limit)
