from __future__ import annotations

import orjson
from fastapi import APIRouter
from fastapi.responses import Response

from api.dependencies import DB, Cache
from api.repositories import station_repository as repo

router = APIRouter(prefix="/filters", tags=["filters"])

_CACHE_KEY = "filters:all"
_TTL       = 300


@router.get("")
async def get_filters(session: DB, cache: Cache) -> Response:
    if cache:
        raw = await cache.get(_CACHE_KEY)
        if raw:
            return Response(content=raw, media_type="application/json")

    data = await repo.get_filter_options(session)
    body = orjson.dumps(data)

    if cache:
        await cache.setex(_CACHE_KEY, _TTL, body)

    return Response(content=body, media_type="application/json")
