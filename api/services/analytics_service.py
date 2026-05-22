from __future__ import annotations

import orjson
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories import analytics_repository as repo
from api.schemas.responses import (
    AcDcBreakdown,
    ChargerSpeedItem,
    CityDistributionItem,
    OperatorDistributionItem,
    OverviewStats,
    StateDistributionItem,
)

_TTL = 300  # 5 minutes


def _dumps(obj) -> bytes:
    """orjson.dumps with Decimal-tolerant fallback."""
    return orjson.dumps(obj, default=str)


async def _cached(
    cache: aioredis.Redis | None,
    key: str,
    fn,
    model,
    is_list: bool = True,
):
    if cache:
        raw = await cache.get(key)
        if raw:
            data = orjson.loads(raw)
            return [model.model_validate(d) for d in data] if is_list else model.model_validate(data)

    result = await fn()

    if cache:
        if is_list:
            payload = _dumps([r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in result])
        else:
            payload = _dumps(result.model_dump(mode="json") if hasattr(result, "model_dump") else result)
        await cache.setex(key, _TTL, payload)

    return result


async def overview(session: AsyncSession, cache: aioredis.Redis | None) -> OverviewStats:
    key = "analytics:overview"
    if cache:
        raw = await cache.get(key)
        if raw:
            return OverviewStats.model_validate(orjson.loads(raw))
    row = await repo.get_overview(session)
    result = OverviewStats.model_validate(row)
    if cache:
        await cache.setex(key, _TTL, _dumps(result.model_dump(mode="json")))
    return result


async def state_distribution(
    session: AsyncSession, cache: aioredis.Redis | None
) -> list[StateDistributionItem]:
    return await _cached(
        cache, "analytics:state_dist",
        lambda: repo.get_state_distribution(session),
        StateDistributionItem,
    )


async def operator_distribution(
    session: AsyncSession, cache: aioredis.Redis | None
) -> list[OperatorDistributionItem]:
    return await _cached(
        cache, "analytics:operator_dist",
        lambda: repo.get_operator_distribution(session),
        OperatorDistributionItem,
    )


async def charger_speed(
    session: AsyncSession, cache: aioredis.Redis | None
) -> list[ChargerSpeedItem]:
    return await _cached(
        cache, "analytics:charger_speed",
        lambda: repo.get_charger_speed(session),
        ChargerSpeedItem,
    )


async def ac_dc_breakdown(
    session: AsyncSession, cache: aioredis.Redis | None
) -> AcDcBreakdown | None:
    key = "analytics:ac_dc"
    if cache:
        raw = await cache.get(key)
        if raw:
            return AcDcBreakdown.model_validate(orjson.loads(raw))
    row = await repo.get_ac_dc_breakdown(session)
    if not row:
        return None
    result = AcDcBreakdown.model_validate(row)
    if cache:
        await cache.setex(key, _TTL, _dumps(result.model_dump(mode="json")))
    return result
