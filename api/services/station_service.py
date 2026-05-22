from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from api.pagination import PaginatedResponse, StationAggStats, make_page
from api.repositories import station_repository as repo
from api.schemas.requests import StationFilters
from api.schemas.responses import (
    ChargerOut,
    ConnectorOut,
    StationDetail,
    StationSummary,
)


async def get_stations_page(
    session: AsyncSession,
    filters: StationFilters,
) -> PaginatedResponse[StationSummary]:
    rows, total, agg = await repo.list_stations(session, filters)
    items = [StationSummary.model_validate(r) for r in rows]
    stats = StationAggStats(
        total_stations=int(agg.get("total_stations", 0)),
        available_stations=int(agg.get("available_stations", 0)),
        total_chargers=int(agg.get("total_chargers", 0)),
        total_connectors=int(agg.get("total_connectors", 0)),
        cities_covered=int(agg.get("cities_covered", 0)),
        operators_count=int(agg.get("operators_count", 0)),
    )
    return make_page(items, total, filters.page, filters.page_size, stats)


async def get_station_detail(
    session: AsyncSession,
    station_id: int,
    cache: aioredis.Redis | None = None,
) -> StationDetail | None:
    cache_key = f"station:{station_id}"

    if cache:
        cached = await cache.get(cache_key)
        if cached:
            return StationDetail.model_validate_json(cached)

    station_row = await repo.get_station(session, station_id)
    if not station_row:
        return None

    # Fire child queries in parallel
    chargers_rows, connectors_rows, amenities_rows, nearby_rows, review_row = (
        await asyncio.gather(
            repo.get_chargers(session, station_id),
            repo.get_connectors_for_station(session, station_id),
            repo.get_amenities(session, station_id),
            repo.get_nearby(session, station_id),
            repo.get_review_summary(session, station_id),
        )
    )

    # Build chargers with nested connectors
    connectors_by_charger: dict[int, list[ConnectorOut]] = {}
    for c in connectors_rows:
        co = ConnectorOut.model_validate(c)
        connectors_by_charger.setdefault(c["charger_id"], []).append(co)

    chargers = [
        ChargerOut(
            **{k: v for k, v in ch.items()},
            connectors=connectors_by_charger.get(ch["id"], []),
        )
        for ch in chargers_rows
    ]

    detail = StationDetail(
        **station_row,
        chargers=chargers,
        amenities=[a for a in amenities_rows],
        nearby_stations=[n for n in nearby_rows],
        review_summary=review_row,
    )

    if cache:
        await cache.setex(cache_key, 120, detail.model_dump_json())

    return detail
