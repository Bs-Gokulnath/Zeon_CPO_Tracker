from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.requests import SortBy, StationFilters


_SORT_SQL: dict[str, str] = {
    SortBy.rating:          "s.avg_rating DESC NULLS LAST, s.id",
    SortBy.power:           "s.highest_power_kw DESC NULLS LAST, s.id",
    SortBy.price_asc:       "LEAST(COALESCE(s.min_ac_price,99999),COALESCE(s.min_dc_price,99999)) ASC NULLS LAST, s.id",
    SortBy.price_desc:      "LEAST(COALESCE(s.min_ac_price,99999),COALESCE(s.min_dc_price,99999)) DESC NULLS LAST, s.id",
    SortBy.connector_count: "s.total_connector_count DESC, s.id",
    SortBy.charger_count:   "s.total_charger_count DESC, s.id",
    SortBy.name:            "s.station_name ASC NULLS LAST",
    SortBy.id:              "s.id ASC",
}

_SUMMARY_COLS = """
    s.id, s.station_name, s.city_name_cached, s.operator_name_cached,
    s.latitude, s.longitude, s.availability, s.charger_type,
    s.highest_power_kw, s.total_charger_count, s.available_connector_count,
    s.avg_rating, s.review_count, s.access_type,
    s.min_ac_price, s.min_dc_price, s.has_amenities, s.scraped_at
"""


def _build_where(f: StationFilters) -> tuple[str, dict]:
    conds: list[str] = []
    p: dict = {}

    if f.state_id is not None:
        conds.append("s.state_id = :state_id")
        p["state_id"] = f.state_id
    if f.city_id is not None:
        conds.append("s.city_id = :city_id")
        p["city_id"] = f.city_id
    if f.operator_id is not None:
        conds.append("s.operator_id = :operator_id")
        p["operator_id"] = f.operator_id
    if f.charger_type is not None:
        conds.append("s.charger_type = :charger_type")
        p["charger_type"] = f.charger_type
    if f.access_type is not None:
        conds.append("s.access_type = :access_type")
        p["access_type"] = f.access_type
    if f.availability is not None:
        conds.append("s.availability = :availability")
        p["availability"] = f.availability
    if f.min_kw is not None:
        conds.append("s.highest_power_kw >= :min_kw")
        p["min_kw"] = f.min_kw
    if f.max_kw is not None:
        conds.append("s.highest_power_kw <= :max_kw")
        p["max_kw"] = f.max_kw
    if f.min_price is not None:
        conds.append(
            "LEAST(COALESCE(s.min_ac_price,99999),COALESCE(s.min_dc_price,99999)) >= :min_price"
        )
        p["min_price"] = f.min_price
    if f.max_price is not None:
        conds.append(
            "LEAST(COALESCE(s.min_ac_price,99999),COALESCE(s.min_dc_price,99999)) <= :max_price"
        )
        p["max_price"] = f.max_price
    if f.min_rating is not None:
        conds.append("s.avg_rating >= :min_rating")
        p["min_rating"] = f.min_rating
    if f.has_amenities is not None:
        conds.append("s.has_amenities = :has_amenities")
        p["has_amenities"] = f.has_amenities
    if f.connector_type_id is not None:
        conds.append(
            "EXISTS (SELECT 1 FROM connectors c2"
            " WHERE c2.station_id = s.id AND c2.connector_type_id = :connector_type_id)"
        )
        p["connector_type_id"] = f.connector_type_id
    if f.q:
        conds.append("s.search_vector @@ plainto_tsquery('simple', :q)")
        p["q"] = f.q

    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    return where, p


async def list_stations(
    session: AsyncSession,
    filters: StationFilters,
) -> tuple[list[dict], int, dict]:
    where, params = _build_where(filters)
    order  = _SORT_SQL.get(filters.sort_by, _SORT_SQL[SortBy.id])
    offset = (filters.page - 1) * filters.page_size

    agg_sql = f"""
        SELECT
            COUNT(*)                                                                AS total_stations,
            COUNT(*) FILTER (WHERE s.availability = 'Available')                   AS available_stations,
            COALESCE(SUM(s.total_charger_count),   0)                              AS total_chargers,
            COALESCE(SUM(s.total_connector_count), 0)                              AS total_connectors,
            COUNT(DISTINCT s.city_id)                                              AS cities_covered,
            COUNT(DISTINCT s.operator_id) FILTER (WHERE s.operator_id IS NOT NULL) AS operators_count
        FROM stations s {where}
    """
    data_sql = f"""
        SELECT {_SUMMARY_COLS}
        FROM stations s
        {where}
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """

    agg_result = await session.execute(text(agg_sql), params)
    agg = dict(agg_result.first()._mapping)
    total: int = int(agg["total_stations"])

    data_result = await session.execute(
        text(data_sql),
        {**params, "limit": filters.page_size, "offset": offset},
    )
    return [dict(r._mapping) for r in data_result], total, agg


async def list_geo_points(
    session: AsyncSession,
    filters: StationFilters,
) -> list[dict]:
    """Return minimal coordinate data for all matching stations (no pagination)."""
    where, params = _build_where(filters)
    coord_cond = "s.latitude IS NOT NULL AND s.longitude IS NOT NULL"
    if where:
        full_where = f"{where} AND {coord_cond}"
    else:
        full_where = f"WHERE {coord_cond}"
    sql = f"""
        SELECT s.id, s.latitude, s.longitude, s.availability, s.charger_type
        FROM stations s
        {full_where}
        ORDER BY s.id
    """
    rows = await session.execute(text(sql), params)
    return [dict(r._mapping) for r in rows]


async def get_station(session: AsyncSession, station_id: int) -> dict | None:
    sql = """
        SELECT
            s.*,
            c.name  AS city_name,
            st.name AS state_name,
            o.name  AS operator_name
        FROM stations s
        LEFT JOIN cities    c  ON c.id  = s.city_id
        LEFT JOIN states    st ON st.id = s.state_id
        LEFT JOIN operators o  ON o.id  = s.operator_id
        WHERE s.id = :station_id
    """
    row = await session.execute(text(sql), {"station_id": station_id})
    r = row.first()
    return dict(r._mapping) if r else None


async def get_chargers(session: AsyncSession, station_id: int) -> list[dict]:
    sql = """
        SELECT id, charger_name, type, power_rating_kw,
               price, currency, price_display,
               connector_count, available_connector_count
        FROM chargers WHERE station_id = :station_id
        ORDER BY id
    """
    rows = await session.execute(text(sql), {"station_id": station_id})
    return [dict(r._mapping) for r in rows]


async def get_connectors_for_station(
    session: AsyncSession, station_id: int
) -> list[dict]:
    sql = """
        SELECT id, charger_id, display_id, connector_type, connector_type_id,
               availability, connector_status, error_message, connector_image
        FROM connectors WHERE station_id = :station_id
        ORDER BY charger_id, id
    """
    rows = await session.execute(text(sql), {"station_id": station_id})
    return [dict(r._mapping) for r in rows]


async def get_amenities(session: AsyncSession, station_id: int) -> list[dict]:
    sql = """
        SELECT a.id, a.type, a.icon
        FROM station_amenities sa
        JOIN amenities a ON a.id = sa.amenity_id
        WHERE sa.station_id = :station_id
        ORDER BY a.type
    """
    rows = await session.execute(text(sql), {"station_id": station_id})
    return [dict(r._mapping) for r in rows]


async def get_nearby(session: AsyncSession, station_id: int) -> list[dict]:
    sql = """
        SELECT nearby_station_id, station_name, latitude, longitude,
               access_type, avg_review_rating, is_connected,
               station_types, branding_logo
        FROM nearby_stations
        WHERE source_station_id = :station_id
        ORDER BY avg_review_rating DESC NULLS LAST
        LIMIT 10
    """
    rows = await session.execute(text(sql), {"station_id": station_id})
    return [dict(r._mapping) for r in rows]


async def get_review_summary(session: AsyncSession, station_id: int) -> dict | None:
    sql = """
        SELECT avg_rating, review_count,
               rating_1_count, rating_2_count, rating_3_count,
               rating_4_count, rating_5_count
        FROM reviews_summary WHERE station_id = :station_id
    """
    row = await session.execute(text(sql), {"station_id": station_id})
    r = row.first()
    return dict(r._mapping) if r else None


# ── Filters ───────────────────────────────────────────────────────────────────

async def get_filter_options(session: AsyncSession) -> dict:
    states = await session.execute(
        text("SELECT id, name, code FROM states ORDER BY name")
    )
    cities = await session.execute(
        text("SELECT id, name, state_id FROM cities ORDER BY name")
    )
    operators = await session.execute(
        text("SELECT id, name, operator_type FROM operators ORDER BY name")
    )
    charger_types = await session.execute(
        text("SELECT DISTINCT charger_type FROM stations WHERE charger_type IS NOT NULL ORDER BY 1")
    )
    connector_types = await session.execute(
        text("SELECT id, connector_name AS name FROM connector_types ORDER BY id")
    )
    access_types = await session.execute(
        text("SELECT DISTINCT access_type FROM stations WHERE access_type IS NOT NULL ORDER BY 1")
    )
    price_range = await session.execute(text("""
        SELECT
            MIN(LEAST(COALESCE(min_ac_price,999999),COALESCE(min_dc_price,999999))) AS min_price,
            MAX(GREATEST(COALESCE(max_ac_price,0),COALESCE(max_dc_price,0)))        AS max_price
        FROM stations
        WHERE min_ac_price IS NOT NULL OR min_dc_price IS NOT NULL
    """))

    rating_buckets = [
        {"label": "4.5+",  "min": 4.5, "max": None},
        {"label": "4.0+",  "min": 4.0, "max": None},
        {"label": "3.5+",  "min": 3.5, "max": None},
        {"label": "Unrated", "min": None, "max": None},
    ]
    pr = price_range.first()

    return {
        "states":          [dict(r._mapping) for r in states],
        "cities":          [dict(r._mapping) for r in cities],
        "operators":       [dict(r._mapping) for r in operators],
        "charger_types":   [r[0] for r in charger_types],
        "connector_types": [dict(r._mapping) for r in connector_types],
        "access_types":    [r[0] for r in access_types],
        "price_range":     {"min": float(pr[0]) if pr and pr[0] else 0,
                            "max": float(pr[1]) if pr and pr[1] else 0},
        "rating_buckets":  rating_buckets,
    }
