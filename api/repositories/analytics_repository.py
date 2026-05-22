from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _add_in(conds: list[str], p: dict, column: str, values, prefix: str) -> None:
    vals = values if isinstance(values, list) else ([values] if values is not None else [])
    if not vals:
        return
    phs = ", ".join(f":{prefix}_{i}" for i in range(len(vals)))
    conds.append(f"{column} IN ({phs})")
    for i, v in enumerate(vals):
        p[f"{prefix}_{i}"] = v


async def get_filtered_overview(session: AsyncSession, **f) -> dict:
    """Overview stats scoped to an arbitrary filter set (same params as stations)."""
    conds: list[str] = []
    p: dict = {}

    _add_in(conds, p, "s.state_id",    f.get("state_id"),    "state_id")
    _add_in(conds, p, "s.city_id",     f.get("city_id"),     "city_id")
    _add_in(conds, p, "s.operator_id", f.get("operator_id"), "operator_id")
    _add_in(conds, p, "s.charger_type", f.get("charger_type"), "charger_type")
    _add_in(conds, p, "s.access_type", f.get("access_type"),  "access_type")
    if f.get("availability") is not None:
        conds.append("s.availability = :availability"); p["availability"] = f["availability"]
    if f.get("min_kw") is not None:
        conds.append("s.highest_power_kw >= :min_kw"); p["min_kw"] = f["min_kw"]
    if f.get("max_kw") is not None:
        conds.append("s.highest_power_kw <= :max_kw"); p["max_kw"] = f["max_kw"]
    if f.get("min_price") is not None:
        conds.append("LEAST(COALESCE(s.min_ac_price,99999),COALESCE(s.min_dc_price,99999)) >= :min_price")
        p["min_price"] = f["min_price"]
    if f.get("max_price") is not None:
        conds.append("LEAST(COALESCE(s.min_ac_price,99999),COALESCE(s.min_dc_price,99999)) <= :max_price")
        p["max_price"] = f["max_price"]
    if f.get("min_rating") is not None:
        conds.append("s.avg_rating >= :min_rating"); p["min_rating"] = f["min_rating"]
    if f.get("connector_type_id") is not None:
        conds.append(
            "EXISTS (SELECT 1 FROM connectors c2 WHERE c2.station_id = s.id"
            " AND c2.connector_type_id = :connector_type_id)"
        )
        p["connector_type_id"] = f["connector_type_id"]

    where = ("WHERE " + " AND ".join(conds)) if conds else ""

    row = await session.execute(text(f"""
        SELECT
            COUNT(*)                                                           AS total_stations,
            COUNT(*) FILTER (WHERE s.availability = 'Available')              AS available_stations,
            COALESCE(SUM(s.total_charger_count),   0)                         AS total_chargers,
            COALESCE(SUM(s.total_connector_count), 0)                         AS total_connectors,
            COUNT(*) FILTER (WHERE s.charger_type = 'AC')                     AS ac_stations,
            COUNT(*) FILTER (WHERE s.charger_type = 'DC')                     AS dc_stations,
            COUNT(*) FILTER (WHERE s.charger_type = 'Mixed')                  AS mixed_stations,
            ROUND(AVG(s.avg_rating) FILTER (WHERE s.avg_rating IS NOT NULL), 2) AS avg_rating,
            COUNT(DISTINCT s.state_id)                                         AS states_covered,
            COUNT(DISTINCT s.city_id)                                          AS cities_covered,
            COUNT(DISTINCT s.operator_id) FILTER (WHERE s.operator_id IS NOT NULL) AS operators_count
        FROM stations s
        {where}
    """), p)
    r = row.first()
    return dict(r._mapping)


async def get_overview(session: AsyncSession) -> dict:
    row = await session.execute(text("""
        SELECT
            COUNT(*)                                                           AS total_stations,
            COUNT(*) FILTER (WHERE availability = 'Available')                AS available_stations,
            COALESCE(SUM(total_charger_count),   0)                           AS total_chargers,
            COALESCE(SUM(total_connector_count), 0)                           AS total_connectors,
            COUNT(*) FILTER (WHERE charger_type = 'AC')                       AS ac_stations,
            COUNT(*) FILTER (WHERE charger_type = 'DC')                       AS dc_stations,
            COUNT(*) FILTER (WHERE charger_type = 'Mixed')                    AS mixed_stations,
            ROUND(AVG(avg_rating) FILTER (WHERE avg_rating IS NOT NULL), 2)   AS avg_rating,
            COUNT(DISTINCT state_id)                                           AS states_covered,
            COUNT(DISTINCT city_id)                                            AS cities_covered,
            COUNT(DISTINCT operator_id) FILTER (WHERE operator_id IS NOT NULL) AS operators_count
        FROM stations
    """))
    r = row.first()
    return dict(r._mapping)


async def get_state_distribution(session: AsyncSession) -> list[dict]:
    rows = await session.execute(text(
        "SELECT * FROM mv_state_station_distribution ORDER BY total_stations DESC"
    ))
    return [dict(r._mapping) for r in rows]


async def get_city_distribution(session: AsyncSession, limit: int = 50) -> list[dict]:
    rows = await session.execute(
        text("SELECT * FROM mv_city_station_distribution ORDER BY total_stations DESC LIMIT :limit"),
        {"limit": limit},
    )
    return [dict(r._mapping) for r in rows]


async def get_operator_distribution(session: AsyncSession) -> list[dict]:
    rows = await session.execute(text(
        "SELECT * FROM mv_operator_distribution ORDER BY total_stations DESC"
    ))
    return [dict(r._mapping) for r in rows]


async def get_charger_speed(session: AsyncSession) -> list[dict]:
    rows = await session.execute(text(
        "SELECT * FROM mv_charger_speed_distribution ORDER BY min_power_kw ASC NULLS LAST"
    ))
    return [dict(r._mapping) for r in rows]


async def get_ac_dc_breakdown(session: AsyncSession) -> dict | None:
    row = await session.execute(text("SELECT * FROM mv_ac_dc_breakdown LIMIT 1"))
    r = row.first()
    return dict(r._mapping) if r else None
