from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Query

from api.dependencies import DB, Cache
from api.pagination import PaginatedResponse
from api.schemas.requests import SortBy, StationFilters
from api.schemas.responses import StationDetail, StationSummary, MapPoint
from api.services import station_service as svc
from scraper.parsers.rsc_parser import parse_rsc_payload, RSCParseError

router = APIRouter(prefix="/stations", tags=["stations"])

# ── Live status cache (30-second TTL per station) ─────────────────────────────
_LIVE_CACHE: dict[int, tuple[float, dict]] = {}
_LIVE_TTL   = 30   # seconds
_LIVE_HEADERS = {
    "RSC": "1",
    "Accept": "text/x-component",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@router.get("", response_model=PaginatedResponse[StationSummary])
async def list_stations(
    session:          DB,
    cache:            Cache,
    state_id:         list[int]   = Query(default=[]),
    city_id:          list[int]   = Query(default=[]),
    operator_id:      list[int]   = Query(default=[]),
    charger_type:     list[str]   = Query(default=[]),
    access_type:      list[str]   = Query(default=[]),
    connector_type_id:int | None  = Query(None),
    availability:     str | None  = Query(None),
    min_kw:           float | None = Query(None, ge=0),
    max_kw:           float | None = Query(None, ge=0),
    min_price:        float | None = Query(None, ge=0),
    max_price:        float | None = Query(None, ge=0),
    min_rating:       float | None = Query(None, ge=0, le=5),
    has_amenities:    bool | None  = Query(None),
    q:                str | None   = Query(None, max_length=100),
    sort_by:          SortBy       = Query(SortBy.id),
    page:             int          = Query(1, ge=1),
    page_size:        int          = Query(50, ge=1, le=200),
) -> PaginatedResponse[StationSummary]:
    filters = StationFilters(
        state_id=state_id, city_id=city_id, operator_id=operator_id,
        charger_type=charger_type, access_type=access_type,
        connector_type_id=connector_type_id, availability=availability,
        min_kw=min_kw, max_kw=max_kw, min_price=min_price, max_price=max_price,
        min_rating=min_rating, has_amenities=has_amenities,
        q=q, sort_by=sort_by, page=page, page_size=page_size,
    )
    return await svc.get_stations_page(session, filters)


@router.get("/geo", response_model=list[MapPoint])
async def list_geo_points(
    session:          DB,
    state_id:         list[int]   = Query(default=[]),
    city_id:          list[int]   = Query(default=[]),
    operator_id:      list[int]   = Query(default=[]),
    charger_type:     list[str]   = Query(default=[]),
    access_type:      list[str]   = Query(default=[]),
    connector_type_id:int | None  = Query(None),
    availability:     str | None  = Query(None),
    min_kw:           float | None = Query(None, ge=0),
    max_kw:           float | None = Query(None, ge=0),
    min_price:        float | None = Query(None, ge=0),
    max_price:        float | None = Query(None, ge=0),
    min_rating:       float | None = Query(None, ge=0, le=5),
    has_amenities:    bool | None  = Query(None),
    q:                str | None   = Query(None, max_length=100),
) -> list[MapPoint]:
    filters = StationFilters(
        state_id=state_id, city_id=city_id, operator_id=operator_id,
        charger_type=charger_type, access_type=access_type,
        connector_type_id=connector_type_id, availability=availability,
        min_kw=min_kw, max_kw=max_kw, min_price=min_price, max_price=max_price,
        min_rating=min_rating, has_amenities=has_amenities, q=q,
    )
    from api.repositories import station_repository as repo
    rows = await repo.list_geo_points(session, filters)
    return [MapPoint.model_validate(r) for r in rows]


@router.get("/{station_id}/live")
async def get_live_status(station_id: int) -> dict:
    """Fetch real-time availability + connector status directly from Statiq."""
    cached = _LIVE_CACHE.get(station_id)
    if cached and (time.monotonic() - cached[0]) < _LIVE_TTL:
        return {**cached[1], "from_cache": True}

    url = f"https://www.statiq.in/x-ev-charging-station-id-{station_id}?__flight__=1"
    # Stream the response with http2 — the station data arrives in the first ~30 KB;
    # HTTP/1.1 times out because the server keeps the connection open waiting for
    # client-side navigation signals that never come.
    buffer = ""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=8.0, read=20.0, write=5.0, pool=5.0),
            follow_redirects=True,
            http2=True,
        ) as client:
            async with client.stream("GET", url, headers=_LIVE_HEADERS) as resp:
                if resp.status_code >= 400:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Statiq returned {resp.status_code}",
                    )
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    # Stop streaming once we have the stationData block
                    if "stationData" in buffer and '"plugin_details"' in buffer:
                        break
                    if len(buffer) > 400_000:
                        break
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Statiq API timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Statiq: {e}")

    try:
        raw = parse_rsc_payload(buffer)
    except RSCParseError as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse Statiq response: {e}")

    data = raw.get("data", {})

    connectors = []
    for plugin in data.get("plugin_details", []):
        charger_id = plugin.get("charger_id")
        for conn in plugin.get("connectors", []):
            connectors.append({
                "charger_id":     charger_id,
                "connector_id":   conn.get("connector_id"),
                "display_id":     conn.get("display_id"),
                "connector_type": conn.get("connector_type"),
                "available":      conn.get("availability", False),
                "status":         conn.get("connector_status"),
                "error":          conn.get("error_message"),
            })

    closing = data.get("closing_status") or {}
    result = {
        "station_id":     station_id,
        "availability":   data.get("availability"),
        "is_connected":   data.get("is_connected"),
        "closing_status": closing.get("text"),        # e.g. "Open Now", "Closed"
        "connectors":     connectors,
        "fetched_at":     datetime.now(timezone.utc).isoformat(),
        "from_cache":     False,
    }

    _LIVE_CACHE[station_id] = (time.monotonic(), result)
    return result


@router.get("/{station_id}", response_model=StationDetail)
async def get_station(
    station_id: int,
    session:    DB,
    cache:      Cache,
) -> StationDetail:
    detail = await svc.get_station_detail(session, station_id, cache)
    if detail is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return detail
