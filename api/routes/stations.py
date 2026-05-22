from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.dependencies import DB, Cache
from api.pagination import PaginatedResponse
from api.schemas.requests import SortBy, StationFilters
from api.schemas.responses import StationDetail, StationSummary, MapPoint
from api.services import station_service as svc

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=PaginatedResponse[StationSummary])
async def list_stations(
    session:          DB,
    cache:            Cache,
    state_id:         int | None   = Query(None),
    city_id:          int | None   = Query(None),
    operator_id:      int | None   = Query(None),
    charger_type:     str | None   = Query(None),
    connector_type_id:int | None   = Query(None),
    access_type:      str | None   = Query(None),
    availability:     str | None   = Query(None),
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
        charger_type=charger_type, connector_type_id=connector_type_id,
        access_type=access_type, availability=availability,
        min_kw=min_kw, max_kw=max_kw, min_price=min_price, max_price=max_price,
        min_rating=min_rating, has_amenities=has_amenities,
        q=q, sort_by=sort_by, page=page, page_size=page_size,
    )
    return await svc.get_stations_page(session, filters)


@router.get("/geo", response_model=list[MapPoint])
async def list_geo_points(
    session:          DB,
    state_id:         int | None   = Query(None),
    city_id:          int | None   = Query(None),
    operator_id:      int | None   = Query(None),
    charger_type:     str | None   = Query(None),
    connector_type_id:int | None   = Query(None),
    access_type:      str | None   = Query(None),
    availability:     str | None   = Query(None),
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
        charger_type=charger_type, connector_type_id=connector_type_id,
        access_type=access_type, availability=availability,
        min_kw=min_kw, max_kw=max_kw, min_price=min_price, max_price=max_price,
        min_rating=min_rating, has_amenities=has_amenities, q=q,
    )
    from api.repositories import station_repository as repo
    rows = await repo.list_geo_points(session, filters)
    return [MapPoint.model_validate(r) for r in rows]


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
