from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("database.refresh_views")

MATERIALIZED_VIEWS = [
    "mv_state_station_distribution",
    "mv_city_station_distribution",
    "mv_operator_distribution",
    "mv_charger_speed_distribution",
    "mv_ac_dc_breakdown",
]


async def refresh_all_views(conn: AsyncConnection) -> None:
    """
    Refresh all analytics materialized views after an ETL run.
    Uses CONCURRENTLY so reads are not blocked during refresh.
    """
    for view_name in MATERIALIZED_VIEWS:
        log.info("Refreshing materialized view: {v}", v=view_name)
        await conn.execute(
            text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
        )
        log.info("Refreshed: {v}", v=view_name)
    await conn.commit()
