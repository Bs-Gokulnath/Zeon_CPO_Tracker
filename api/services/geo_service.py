from __future__ import annotations

import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.responses import NearbyResult


_EARTH_KM = 6371.0

_HAVERSINE_SQL = """
    6371 * 2 * ASIN(SQRT(
        POWER(SIN(RADIANS(s.latitude  - :lat) / 2), 2) +
        COS(RADIANS(:lat)) * COS(RADIANS(s.latitude)) *
        POWER(SIN(RADIANS(s.longitude - :lon) / 2), 2)
    ))
"""


async def nearby_stations(
    session: AsyncSession,
    lat: float,
    lon: float,
    radius_km: float,
    charger_type: str | None = None,
    limit: int = 20,
) -> list[NearbyResult]:
    # Bounding-box prefilter to cut rows before the expensive Haversine
    lat_deg = radius_km / 111.32
    lon_deg = radius_km / (111.32 * math.cos(math.radians(lat))) if lat != 90 else 180

    extra = "AND s.charger_type = :charger_type" if charger_type else ""

    sql = f"""
        SELECT *
        FROM (
            SELECT
                s.id, s.station_name, s.latitude, s.longitude,
                s.availability, s.charger_type, s.highest_power_kw,
                s.available_connector_count, s.avg_rating, s.access_type,
                {_HAVERSINE_SQL} AS distance_km
            FROM stations s
            WHERE s.latitude  IS NOT NULL
              AND s.longitude IS NOT NULL
              AND s.latitude  BETWEEN :lat_min AND :lat_max
              AND s.longitude BETWEEN :lon_min AND :lon_max
              {extra}
        ) sub
        WHERE distance_km <= :radius_km
        ORDER BY distance_km ASC
        LIMIT :limit
    """

    params: dict = {
        "lat": lat, "lon": lon,
        "lat_min": lat - lat_deg, "lat_max": lat + lat_deg,
        "lon_min": lon - lon_deg, "lon_max": lon + lon_deg,
        "radius_km": radius_km,
        "limit": limit,
    }
    if charger_type:
        params["charger_type"] = charger_type

    rows = await session.execute(text(sql), params)
    return [NearbyResult.model_validate(dict(r._mapping)) for r in rows]
