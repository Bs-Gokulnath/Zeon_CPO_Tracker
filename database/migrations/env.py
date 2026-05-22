from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base
from scraper.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations against a URL without an active DB connection.
    Emits SQL to stdout — useful for review before applying.
    """
    url = settings.database_url_sync
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(sync_conn) -> None:
    context.configure(
        connection=sync_conn,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations against a live DB using the async engine.
    Alembic's run_sync bridges the async connection to sync DDL operations.
    """
    async_engine = create_async_engine(settings.database_url, echo=False)
    async with async_engine.connect() as conn:
        await conn.run_sync(_do_run_migrations)
    await async_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
