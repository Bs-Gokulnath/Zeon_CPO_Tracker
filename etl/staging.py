from __future__ import annotations

"""
Staging layer: create TEMP tables and bulk-load DataFrames via asyncpg COPY.

TEMP tables are session-scoped and auto-dropped when the connection closes,
giving us free cleanup at the end of each ETL run.
"""

import time

import asyncpg
import pandas as pd

from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.staging")

# ── Column definitions ────────────────────────────────────────────────────────
# Each list defines exactly the columns that will be COPY'd into the staging
# table.  Order matters: DataFrame must present columns in this order.

STG_STATION_COLS = [
    "id", "station_name", "city_name", "state_name",
    "operator_normalized_name", "operator_type",
    "address", "area", "landmark",
    "latitude", "longitude",
    "access_type", "availability", "is_connected", "operational_time",
    "charger_type", "highest_power_kw", "avg_rating", "review_count",
    "ac_charger_count", "dc_charger_count", "total_charger_count",
    "total_connector_count", "available_connector_count",
    "min_ac_price", "max_ac_price", "min_dc_price", "max_dc_price",
    "has_amenities", "station_image_url", "station_banner", "navigation_link",
    "scraped_at", "run_id", "content_hash",
]

STG_CHARGER_COLS = [
    "id", "station_id", "charger_name", "type", "power_rating_kw",
    "price", "currency", "price_display", "last_used_on",
    "connector_count", "available_connector_count",
]

STG_CONNECTOR_COLS = [
    "id", "charger_id", "station_id", "display_id",
    "connector_type", "connector_type_id",
    "availability", "connector_status", "error_message", "connector_image",
]

STG_AMENITY_COLS = [
    "amenity_id", "station_id", "type", "icon", "map_id",
]

STG_NEARBY_COLS = [
    "source_station_id", "nearby_station_id", "station_name",
    "latitude", "longitude", "access_type", "access_type_int",
    "avg_review_rating", "is_connected", "station_types", "branding_logo",
]

# ── DDL for each staging table ────────────────────────────────────────────────

_STG_DDL = {
    "stg_stations": """
        CREATE TEMP TABLE IF NOT EXISTS stg_stations (
            id                        INTEGER,
            station_name              TEXT,
            city_name                 TEXT,
            state_name                TEXT,
            operator_normalized_name  TEXT,
            operator_type             TEXT,
            address                   TEXT,
            area                      TEXT,
            landmark                  TEXT,
            latitude                  DOUBLE PRECISION,
            longitude                 DOUBLE PRECISION,
            access_type               TEXT,
            availability              TEXT,
            is_connected              BOOLEAN,
            operational_time          TEXT,
            charger_type              TEXT,
            highest_power_kw          NUMERIC,
            avg_rating                NUMERIC,
            review_count              INTEGER,
            ac_charger_count          INTEGER,
            dc_charger_count          INTEGER,
            total_charger_count       INTEGER,
            total_connector_count     INTEGER,
            available_connector_count INTEGER,
            min_ac_price              NUMERIC,
            max_ac_price              NUMERIC,
            min_dc_price              NUMERIC,
            max_dc_price              NUMERIC,
            has_amenities             BOOLEAN,
            station_image_url         TEXT,
            station_banner            TEXT,
            navigation_link           TEXT,
            scraped_at                TEXT,
            run_id                    TEXT,
            content_hash              TEXT
        )
    """,
    "stg_chargers": """
        CREATE TEMP TABLE IF NOT EXISTS stg_chargers (
            id                        INTEGER,
            station_id                INTEGER,
            charger_name              TEXT,
            type                      TEXT,
            power_rating_kw           NUMERIC,
            price                     NUMERIC,
            currency                  TEXT,
            price_display             TEXT,
            last_used_on              TEXT,
            connector_count           INTEGER,
            available_connector_count INTEGER
        )
    """,
    "stg_connectors": """
        CREATE TEMP TABLE IF NOT EXISTS stg_connectors (
            id                INTEGER,
            charger_id        INTEGER,
            station_id        INTEGER,
            display_id        INTEGER,
            connector_type    TEXT,
            connector_type_id INTEGER,
            availability      BOOLEAN,
            connector_status  TEXT,
            error_message     TEXT,
            connector_image   TEXT
        )
    """,
    "stg_amenities": """
        CREATE TEMP TABLE IF NOT EXISTS stg_amenities (
            amenity_id  INTEGER,
            station_id  INTEGER,
            type        TEXT,
            icon        TEXT,
            map_id      INTEGER
        )
    """,
    "stg_nearby_stations": """
        CREATE TEMP TABLE IF NOT EXISTS stg_nearby_stations (
            source_station_id  INTEGER,
            nearby_station_id  INTEGER,
            station_name       TEXT,
            latitude           DOUBLE PRECISION,
            longitude          DOUBLE PRECISION,
            access_type        TEXT,
            access_type_int    INTEGER,
            avg_review_rating  NUMERIC,
            is_connected       BOOLEAN,
            station_types      TEXT,
            branding_logo      TEXT
        )
    """,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    """
    Extract `columns` from df, replace NaN with None, return list of tuples
    suitable for asyncpg copy_records_to_table.
    """
    # Add any missing columns as None
    for col in columns:
        if col not in df.columns:
            df[col] = None

    sub = df[columns].copy()
    # NaN → None: works for all dtypes including object columns
    sub = sub.where(pd.notna(sub), None)
    return [tuple(row) for row in sub.values.tolist()]


# ── Public API ────────────────────────────────────────────────────────────────

async def create_staging_tables(conn: asyncpg.Connection) -> None:
    for name, ddl in _STG_DDL.items():
        await conn.execute(ddl)
    # Composite index on nearby staging table speeds up ON CONFLICT resolution
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stg_nearby_pk
            ON stg_nearby_stations (source_station_id, nearby_station_id)
    """)
    log.debug("Staging tables created")


async def copy_to_staging(
    conn: asyncpg.Connection,
    *,
    stations: pd.DataFrame,
    chargers: pd.DataFrame,
    connectors: pd.DataFrame,
    amenities: pd.DataFrame,
    nearby_stations: pd.DataFrame,
) -> dict[str, float]:
    """
    Bulk-load all DataFrames into their staging tables via asyncpg COPY.
    Returns dict of {table_name: elapsed_secs}.
    """
    tasks = [
        ("stg_stations",        stations,       STG_STATION_COLS),
        ("stg_chargers",        chargers,       STG_CHARGER_COLS),
        ("stg_connectors",      connectors,     STG_CONNECTOR_COLS),
        ("stg_amenities",       amenities,      STG_AMENITY_COLS),
        ("stg_nearby_stations", nearby_stations, STG_NEARBY_COLS),
    ]
    timings: dict[str, float] = {}
    for table_name, df, columns in tasks:
        if df.empty:
            log.debug("Skipping COPY for {t} — empty DataFrame", t=table_name)
            timings[table_name] = 0.0
            continue

        records = _df_to_records(df, columns)
        t0 = time.monotonic()
        await conn.copy_records_to_table(
            table_name,
            records=records,
            columns=columns,
        )
        elapsed = time.monotonic() - t0
        timings[table_name] = elapsed
        log.info(
            "COPY {t}: {n:,} rows in {s:.3f}s ({r:.0f} rows/s)",
            t=table_name, n=len(records), s=elapsed,
            r=len(records) / elapsed if elapsed > 0 else 0,
        )

    return timings
