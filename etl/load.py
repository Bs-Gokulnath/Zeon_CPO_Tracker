from __future__ import annotations

"""
Load phase: merge staging tables → production tables.

All merges use INSERT ... ON CONFLICT DO UPDATE (upsert).
FK-safe ordering: dimensions first, then stations, then child tables.

stations uses content_hash to skip rows that haven't changed (no-op update).
"""

from dataclasses import dataclass

import asyncpg

from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.load")


@dataclass
class LoadCounts:
    states: int = 0
    cities: int = 0
    operators: int = 0
    connector_types: int = 0
    amenities: int = 0
    stations_inserted: int = 0
    stations_updated: int = 0
    chargers: int = 0
    connectors: int = 0
    station_amenities: int = 0
    nearby: int = 0
    reviews: int = 0
    history: int = 0


# ── Dimensions ────────────────────────────────────────────────────────────────

async def load_states(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO states (name, code)
        SELECT DISTINCT state_name, NULL
        FROM stg_stations
        WHERE state_name IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)
    n = int(result.split()[-1])
    log.info("states upserted: {n}", n=n)
    return n


async def load_cities(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO cities (name, state_id)
        SELECT DISTINCT s.city_name, st.id
        FROM stg_stations s
        JOIN states st ON st.name = s.state_name
        WHERE s.city_name IS NOT NULL
        ON CONFLICT (name, state_id) DO NOTHING
    """)
    n = int(result.split()[-1])
    log.info("cities upserted: {n}", n=n)
    return n


async def load_operators(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO operators (name, normalized_name, operator_type)
        SELECT DISTINCT operator_normalized_name, operator_normalized_name, operator_type
        FROM stg_stations
        WHERE operator_normalized_name IS NOT NULL
        ON CONFLICT (name) DO UPDATE SET
            operator_type = EXCLUDED.operator_type
        WHERE operators.operator_type IS DISTINCT FROM EXCLUDED.operator_type
    """)
    n = int(result.split()[-1])
    log.info("operators upserted: {n}", n=n)
    return n


async def load_connector_types(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO connector_types (id, connector_name, connector_image_url)
        SELECT DISTINCT connector_type_id, connector_type, NULL
        FROM stg_connectors
        WHERE connector_type_id IS NOT NULL
        ON CONFLICT (id) DO NOTHING
    """)
    n = int(result.split()[-1])
    log.info("connector_types upserted: {n}", n=n)
    return n


async def load_amenities_dim(conn: asyncpg.Connection) -> int:
    """
    Upsert amenity dimension (type as natural key).
    Uses the stg_amenities staging table.
    """
    result = await conn.execute("""
        INSERT INTO amenities (type, icon)
        SELECT DISTINCT type, icon
        FROM stg_amenities
        WHERE type IS NOT NULL
        ON CONFLICT (type) DO NOTHING
    """)
    n = int(result.split()[-1])
    log.info("amenities (dim) upserted: {n}", n=n)
    return n


# ── Stations ──────────────────────────────────────────────────────────────────

async def _has_postgis(conn: asyncpg.Connection) -> bool:
    return bool(await conn.fetchval(
        "SELECT 1 FROM pg_extension WHERE extname = 'postgis'"
    ))


async def load_stations(conn: asyncpg.Connection, run_id: str) -> tuple[int, int]:
    """
    Merge stg_stations → stations.
    Skips rows whose content_hash hasn't changed (WHERE guard).
    Returns (inserted, updated).
    """
    postgis = await _has_postgis(conn)
    loc_col    = ", location" if postgis else ""
    loc_select = (
        ", CASE WHEN s.latitude IS NOT NULL AND s.longitude IS NOT NULL"
        " THEN ST_MakePoint(s.longitude, s.latitude)::geography ELSE NULL END"
        if postgis else ""
    )
    loc_update = "\n                location                  = EXCLUDED.location," if postgis else ""

    rows = await conn.fetch(f"""
        WITH merged AS (
            INSERT INTO stations (
                id, station_name,
                city_id, state_id, operator_id,
                city_name_cached, operator_name_cached,
                address, area, landmark,
                latitude, longitude{loc_col},
                access_type, availability, is_connected, operational_time,
                charger_type, highest_power_kw, avg_rating, review_count,
                ac_charger_count, dc_charger_count, total_charger_count,
                total_connector_count, available_connector_count,
                min_ac_price, max_ac_price, min_dc_price, max_dc_price,
                has_amenities, station_image_url, station_banner, navigation_link,
                scraped_at, run_id, content_hash
            )
            SELECT
                s.id,
                s.station_name,
                c.id                              AS city_id,
                st.id                             AS state_id,
                o.id                              AS operator_id,
                s.city_name                       AS city_name_cached,
                s.operator_normalized_name        AS operator_name_cached,
                s.address, s.area, s.landmark,
                s.latitude, s.longitude{loc_select},
                s.access_type, s.availability, s.is_connected, s.operational_time,
                s.charger_type, s.highest_power_kw, s.avg_rating, s.review_count,
                s.ac_charger_count, s.dc_charger_count, s.total_charger_count,
                s.total_connector_count, s.available_connector_count,
                s.min_ac_price, s.max_ac_price, s.min_dc_price, s.max_dc_price,
                s.has_amenities, s.station_image_url, s.station_banner, s.navigation_link,
                s.scraped_at, s.run_id, s.content_hash
            FROM stg_stations s
            LEFT JOIN states   st ON st.name = s.state_name
            LEFT JOIN cities   c  ON c.name  = s.city_name
                AND c.state_id = st.id
            LEFT JOIN operators o  ON o.name  = s.operator_normalized_name
            ON CONFLICT (id) DO UPDATE SET
                station_name              = EXCLUDED.station_name,
                city_id                   = EXCLUDED.city_id,
                state_id                  = EXCLUDED.state_id,
                operator_id               = EXCLUDED.operator_id,
                city_name_cached          = EXCLUDED.city_name_cached,
                operator_name_cached      = EXCLUDED.operator_name_cached,
                address                   = EXCLUDED.address,
                area                      = EXCLUDED.area,
                landmark                  = EXCLUDED.landmark,
                latitude                  = EXCLUDED.latitude,
                longitude                 = EXCLUDED.longitude,{loc_update}
                access_type               = EXCLUDED.access_type,
                availability              = EXCLUDED.availability,
                is_connected              = EXCLUDED.is_connected,
                operational_time          = EXCLUDED.operational_time,
                charger_type              = EXCLUDED.charger_type,
                highest_power_kw          = EXCLUDED.highest_power_kw,
                avg_rating                = EXCLUDED.avg_rating,
                review_count              = EXCLUDED.review_count,
                ac_charger_count          = EXCLUDED.ac_charger_count,
                dc_charger_count          = EXCLUDED.dc_charger_count,
                total_charger_count       = EXCLUDED.total_charger_count,
                total_connector_count     = EXCLUDED.total_connector_count,
                available_connector_count = EXCLUDED.available_connector_count,
                min_ac_price              = EXCLUDED.min_ac_price,
                max_ac_price              = EXCLUDED.max_ac_price,
                min_dc_price              = EXCLUDED.min_dc_price,
                max_dc_price              = EXCLUDED.max_dc_price,
                has_amenities             = EXCLUDED.has_amenities,
                station_image_url         = EXCLUDED.station_image_url,
                station_banner            = EXCLUDED.station_banner,
                navigation_link           = EXCLUDED.navigation_link,
                scraped_at                = EXCLUDED.scraped_at,
                run_id                    = EXCLUDED.run_id,
                content_hash              = EXCLUDED.content_hash
            WHERE stations.content_hash IS DISTINCT FROM EXCLUDED.content_hash
            RETURNING xmax
        )
        SELECT
            COUNT(*) FILTER (WHERE xmax = 0)  AS inserted,
            COUNT(*) FILTER (WHERE xmax != 0) AS updated
        FROM merged
    """)
    inserted = rows[0]["inserted"] if rows else 0
    updated  = rows[0]["updated"]  if rows else 0
    log.info("stations: {i} inserted, {u} updated", i=inserted, u=updated)
    return inserted, updated


# ── Child tables ──────────────────────────────────────────────────────────────

async def load_chargers(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO chargers (
            id, station_id, charger_name, type, power_rating_kw,
            price, currency, price_display, last_used_on,
            connector_count, available_connector_count
        )
        SELECT
            id, station_id, charger_name, type, power_rating_kw,
            price, currency, price_display, last_used_on,
            connector_count, available_connector_count
        FROM stg_chargers
        ON CONFLICT (id) DO UPDATE SET
            station_id                = EXCLUDED.station_id,
            charger_name              = EXCLUDED.charger_name,
            type                      = EXCLUDED.type,
            power_rating_kw           = EXCLUDED.power_rating_kw,
            price                     = EXCLUDED.price,
            currency                  = EXCLUDED.currency,
            price_display             = EXCLUDED.price_display,
            last_used_on              = EXCLUDED.last_used_on,
            connector_count           = EXCLUDED.connector_count,
            available_connector_count = EXCLUDED.available_connector_count
    """)
    n = int(result.split()[-1])
    log.info("chargers upserted: {n}", n=n)
    return n


async def load_connectors(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO connectors (
            id, charger_id, station_id, display_id,
            connector_type, connector_type_id,
            availability, connector_status, error_message, connector_image
        )
        SELECT
            id, charger_id, station_id, display_id,
            connector_type, connector_type_id,
            availability, connector_status, error_message, connector_image
        FROM stg_connectors
        ON CONFLICT (id) DO UPDATE SET
            charger_id        = EXCLUDED.charger_id,
            station_id        = EXCLUDED.station_id,
            display_id        = EXCLUDED.display_id,
            connector_type    = EXCLUDED.connector_type,
            connector_type_id = EXCLUDED.connector_type_id,
            availability      = EXCLUDED.availability,
            connector_status  = EXCLUDED.connector_status,
            error_message     = EXCLUDED.error_message,
            connector_image   = EXCLUDED.connector_image
    """)
    n = int(result.split()[-1])
    log.info("connectors upserted: {n}", n=n)
    return n


async def load_station_amenities(conn: asyncpg.Connection) -> int:
    """
    Resolve amenity natural-key (type) → amenities.id, then upsert junction.
    """
    result = await conn.execute("""
        INSERT INTO station_amenities (station_id, amenity_id, map_id)
        SELECT DISTINCT sa.station_id, a.id, sa.map_id
        FROM stg_amenities sa
        JOIN amenities a ON a.type = sa.type
        ON CONFLICT (station_id, amenity_id) DO UPDATE SET
            map_id = EXCLUDED.map_id
    """)
    n = int(result.split()[-1])
    log.info("station_amenities upserted: {n}", n=n)
    return n


async def load_nearby_stations(conn: asyncpg.Connection) -> int:
    result = await conn.execute("""
        INSERT INTO nearby_stations (
            source_station_id, nearby_station_id, station_name,
            latitude, longitude, access_type,
            avg_review_rating, is_connected, station_types, branding_logo
        )
        SELECT
            source_station_id, nearby_station_id, station_name,
            latitude, longitude, access_type_int,
            avg_review_rating, is_connected, station_types, branding_logo
        FROM stg_nearby_stations
        ON CONFLICT (source_station_id, nearby_station_id) DO UPDATE SET
            station_name      = EXCLUDED.station_name,
            latitude          = EXCLUDED.latitude,
            longitude         = EXCLUDED.longitude,
            avg_review_rating = EXCLUDED.avg_review_rating,
            is_connected      = EXCLUDED.is_connected,
            station_types     = EXCLUDED.station_types,
            branding_logo     = EXCLUDED.branding_logo
        WHERE nearby_stations.avg_review_rating IS DISTINCT FROM EXCLUDED.avg_review_rating
           OR nearby_stations.is_connected      IS DISTINCT FROM EXCLUDED.is_connected
           OR nearby_stations.station_name      IS DISTINCT FROM EXCLUDED.station_name
           OR nearby_stations.station_types     IS DISTINCT FROM EXCLUDED.station_types
    """)
    n = int(result.split()[-1])
    log.info("nearby_stations upserted: {n}", n=n)
    return n


async def load_reviews_summary(conn: asyncpg.Connection) -> int:
    """
    Upsert reviews_summary from stations data.
    Rating breakdown (r1..r5 counts) is zero-filled — enriched in a later step.
    """
    result = await conn.execute("""
        INSERT INTO reviews_summary (
            station_id, avg_rating, review_count,
            rating_1_count, rating_2_count, rating_3_count,
            rating_4_count, rating_5_count, updated_at
        )
        SELECT
            id,
            avg_rating,
            COALESCE(review_count, 0),
            0, 0, 0, 0, 0,
            NOW()
        FROM stg_stations
        ON CONFLICT (station_id) DO UPDATE SET
            avg_rating   = EXCLUDED.avg_rating,
            review_count = EXCLUDED.review_count,
            updated_at   = EXCLUDED.updated_at
        WHERE reviews_summary.review_count IS DISTINCT FROM EXCLUDED.review_count
           OR reviews_summary.avg_rating   IS DISTINCT FROM EXCLUDED.avg_rating
    """)
    n = int(result.split()[-1])
    log.info("reviews_summary upserted: {n}", n=n)
    return n


async def load_status_history(conn: asyncpg.Connection, run_id: str) -> int:
    """
    Append one history snapshot per station for this run.
    Idempotent: skips stations already recorded for this run.
    """
    result = await conn.execute("""
        INSERT INTO station_status_history (
            station_id, scrape_run_id,
            availability, available_connector_count,
            avg_rating, review_count, scraped_at
        )
        SELECT
            s.id, $1::varchar,
            s.availability, s.available_connector_count,
            s.avg_rating, s.review_count,
            COALESCE(s.scraped_at::timestamptz, NOW())
        FROM stg_stations s
        WHERE NOT EXISTS (
            SELECT 1 FROM station_status_history h
            WHERE h.station_id = s.id
              AND h.scrape_run_id = $1::varchar
        )
    """, run_id)
    n = int(result.split()[-1])
    log.info("station_status_history inserted: {n}", n=n)
    return n


async def load_scrape_run(
    conn: asyncpg.Connection,
    run_id: str,
    quality_report: dict | None = None,
) -> None:
    import orjson
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    qr_str = orjson.dumps(quality_report).decode() if quality_report else None
    await conn.execute("""
        INSERT INTO scrape_runs (run_id, started_at, completed_at, quality_report)
        VALUES ($1, $2, $2, $3)
        ON CONFLICT (run_id) DO UPDATE SET
            completed_at   = EXCLUDED.completed_at,
            quality_report = COALESCE(EXCLUDED.quality_report, scrape_runs.quality_report)
    """, run_id, now, qr_str)
    log.info("scrape_run upserted: {rid}", rid=run_id)


async def load_failed_scrapes(
    conn: asyncpg.Connection,
    run_id: str,
    failed_ids: dict[str, int],
) -> None:
    """Insert failed station records. Idempotent via ON CONFLICT DO NOTHING."""
    if not failed_ids:
        return
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    records = [
        (run_id, int(sid), attempts, now)
        for sid, attempts in failed_ids.items()
    ]
    await conn.executemany("""
        INSERT INTO failed_scrapes (run_id, station_id, attempt_count, scraped_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT DO NOTHING
    """, records)
    log.info("failed_scrapes loaded: {n}", n=len(records))
