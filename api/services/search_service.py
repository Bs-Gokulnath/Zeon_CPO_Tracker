from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.responses import SearchHit


async def search(
    session: AsyncSession,
    q: str,
    limit: int = 10,
) -> list[SearchHit]:
    # tsvector full-text search (GIN index) with trigram fallback for short queries
    if len(q) >= 3:
        sql = """
            SELECT s.id, s.station_name, s.city_name_cached AS city_name,
                   st.name AS state_name, s.charger_type, s.availability
            FROM stations s
            LEFT JOIN states st ON st.id = s.state_id
            WHERE s.search_vector @@ plainto_tsquery('simple', :q)
            ORDER BY ts_rank(s.search_vector, plainto_tsquery('simple', :q)) DESC
            LIMIT :limit
        """
    else:
        # Short query: use trigram similarity on station_name
        sql = """
            SELECT s.id, s.station_name, s.city_name_cached AS city_name,
                   st.name AS state_name, s.charger_type, s.availability
            FROM stations s
            LEFT JOIN states st ON st.id = s.state_id
            WHERE s.station_name ILIKE :pattern
            ORDER BY s.station_name
            LIMIT :limit
        """

    params: dict = {"q": q, "limit": limit} if len(q) >= 3 else {
        "pattern": f"%{q}%", "limit": limit
    }
    rows = await session.execute(text(sql), params)
    return [SearchHit.model_validate(dict(r._mapping)) for r in rows]


async def autocomplete(
    session: AsyncSession,
    q: str,
    limit: int = 10,
) -> list[SearchHit]:
    sql = """
        SELECT s.id, s.station_name, s.city_name_cached AS city_name,
               st.name AS state_name, s.charger_type, s.availability
        FROM stations s
        LEFT JOIN states st ON st.id = s.state_id
        WHERE s.station_name ILIKE :pattern
        ORDER BY s.station_name
        LIMIT :limit
    """
    rows = await session.execute(
        text(sql),
        {"pattern": f"{q}%", "limit": limit},
    )
    return [SearchHit.model_validate(dict(r._mapping)) for r in rows]
