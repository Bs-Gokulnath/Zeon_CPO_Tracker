from __future__ import annotations

from fastapi import APIRouter

from api.dependencies import DB, Cache
from api.schemas.responses import HealthResponse, HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health(session: DB, cache: Cache) -> HealthResponse:
    db_status = HealthStatus(status="ok")
    cache_status = HealthStatus(status="ok")
    etl_run_id: str | None = None
    etl_age_hrs: float | None = None
    stations: int | None = None

    # DB check
    try:
        from sqlalchemy import text
        row = await session.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM stations)                              AS stations,
                (SELECT run_id    FROM scrape_runs ORDER BY completed_at DESC LIMIT 1) AS run_id,
                (SELECT EXTRACT(EPOCH FROM (NOW() - completed_at)) / 3600
                 FROM scrape_runs ORDER BY completed_at DESC LIMIT 1)       AS age_hrs
        """))
        r = row.first()
        if r:
            stations    = r[0]
            etl_run_id  = r[1]
            etl_age_hrs = float(r[2]) if r[2] is not None else None
    except Exception as exc:
        db_status = HealthStatus(status="down", detail=str(exc))

    # Cache check
    if cache is None:
        cache_status = HealthStatus(status="degraded", detail="Redis not configured")
    else:
        try:
            await cache.ping()
        except Exception as exc:
            cache_status = HealthStatus(status="down", detail=str(exc))

    overall = (
        "ok"
        if db_status.status == "ok"
        else "down"
    )
    return HealthResponse(
        status=overall,
        db=db_status,
        cache=cache_status,
        etl_run_id=etl_run_id,
        etl_age_hrs=round(etl_age_hrs, 2) if etl_age_hrs is not None else None,
        stations=stations,
    )


@router.get("/db", response_model=HealthStatus)
async def health_db(session: DB) -> HealthStatus:
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        return HealthStatus(status="ok")
    except Exception as exc:
        return HealthStatus(status="down", detail=str(exc))


@router.get("/cache", response_model=HealthStatus)
async def health_cache(cache: Cache) -> HealthStatus:
    if cache is None:
        return HealthStatus(status="degraded", detail="Redis not configured")
    try:
        await cache.ping()
        return HealthStatus(status="ok")
    except Exception as exc:
        return HealthStatus(status="down", detail=str(exc))
