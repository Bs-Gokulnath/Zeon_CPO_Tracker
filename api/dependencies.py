from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import AsyncSessionFactory
from scraper.config import settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_redis(request: Request) -> aioredis.Redis | None:
    return getattr(request.app.state, "redis", None)


DB    = Annotated[AsyncSession, Depends(get_db)]
Cache = Annotated[aioredis.Redis | None, Depends(get_redis)]
