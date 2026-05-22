from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.middleware import register_middleware
from api.routes import admin, analytics, filters, geo, health, search, stations
from database.engine import engine
from scraper.config import settings
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("API startup — connecting to DB and cache")

    # Test DB pool
    async with engine.connect() as conn:
        from sqlalchemy import text
        await conn.execute(text("SELECT 1"))

    # Redis — graceful degradation if unavailable
    try:
        r = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await r.ping()
        app.state.redis = r
        log.info("Redis connected: {url}", url=settings.redis_url)
    except Exception as exc:
        app.state.redis = None
        log.warning("Redis unavailable ({e}) — caching disabled", e=exc)

    yield

    # Shutdown
    if getattr(app.state, "redis", None):
        await app.state.redis.aclose()
    await engine.dispose()
    log.info("API shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Statiq EV Intelligence API",
        description=(
            "Real-time EV charging station intelligence for India. "
            "Powered by Statiq.in scraper data."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    register_middleware(app)

    app.include_router(health.router)
    app.include_router(admin.router)
    app.include_router(stations.router)
    app.include_router(filters.router)
    app.include_router(analytics.router)
    app.include_router(search.router)
    app.include_router(geo.router)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"service": "statiq-ev-api", "version": "1.0.0", "docs": "/docs"}

    return app


app = create_app()


def start() -> None:
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    start()
