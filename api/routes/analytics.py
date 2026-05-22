from __future__ import annotations

from fastapi import APIRouter, Query

from api.dependencies import DB, Cache
from api.schemas.responses import (
    AcDcBreakdown,
    ChargerSpeedItem,
    CityDistributionItem,
    OperatorDistributionItem,
    OverviewStats,
    StateDistributionItem,
)
from api.services import analytics_service as svc
from api.repositories import analytics_repository as repo

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewStats)
async def overview(
    session: DB,
    cache:   Cache,
    state_id:          list[int]   = Query(default=[]),
    city_id:           list[int]   = Query(default=[]),
    operator_id:       list[int]   = Query(default=[]),
    charger_type:      list[str]   = Query(default=[]),
    access_type:       list[str]   = Query(default=[]),
    connector_type_id: int   | None = Query(None),
    availability:      str   | None = Query(None),
    min_kw:            float | None = Query(None),
    max_kw:            float | None = Query(None),
    min_price:         float | None = Query(None),
    max_price:         float | None = Query(None),
    min_rating:        float | None = Query(None),
) -> OverviewStats:
    filters = dict(
        state_id=state_id, city_id=city_id, operator_id=operator_id,
        charger_type=charger_type, connector_type_id=connector_type_id,
        access_type=access_type, availability=availability,
        min_kw=min_kw, max_kw=max_kw,
        min_price=min_price, max_price=max_price,
        min_rating=min_rating,
    )
    has_filters = any(v is not None and v != [] for v in filters.values())
    if has_filters:
        row = await repo.get_filtered_overview(session, **filters)
        return OverviewStats.model_validate(row)
    return await svc.overview(session, cache)


@router.get("/state-distribution", response_model=list[StateDistributionItem])
async def state_distribution(session: DB, cache: Cache) -> list[StateDistributionItem]:
    return await svc.state_distribution(session, cache)


@router.get("/city-distribution", response_model=list[CityDistributionItem])
async def city_distribution(
    session: DB,
    cache:   Cache,
    limit:   int = Query(50, ge=1, le=500),
) -> list[CityDistributionItem]:
    rows = await repo.get_city_distribution(session, limit)
    return [CityDistributionItem.model_validate(r) for r in rows]


@router.get("/operator-distribution", response_model=list[OperatorDistributionItem])
async def operator_distribution(
    session: DB, cache: Cache
) -> list[OperatorDistributionItem]:
    return await svc.operator_distribution(session, cache)


@router.get("/charger-speed", response_model=list[ChargerSpeedItem])
async def charger_speed(session: DB, cache: Cache) -> list[ChargerSpeedItem]:
    return await svc.charger_speed(session, cache)


@router.get("/ac-dc-breakdown", response_model=AcDcBreakdown)
async def ac_dc_breakdown(session: DB, cache: Cache) -> AcDcBreakdown:
    result = await svc.ac_dc_breakdown(session, cache)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Analytics data not available")
    return result
