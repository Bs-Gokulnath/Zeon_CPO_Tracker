"""Initial schema: all tables, indexes, triggers, and materialized views.

Revision ID: 0001
Revises:
Create Date: 2026-05-21

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _x(sql: str) -> None:
    op.execute(sql)


# ─────────────────────────────────────────────────────────────────────────────
# UPGRADE
# ─────────────────────────────────────────────────────────────────────────────

def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    # pg_trgm is always available; postgis is optional (may not be installed)
    _x("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── scrape_runs ───────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE scrape_runs (
        run_id          VARCHAR(50)  PRIMARY KEY,
        started_at      TIMESTAMPTZ  NOT NULL,
        completed_at    TIMESTAMPTZ,
        total_stations  INTEGER      NOT NULL DEFAULT 0,
        success_count   INTEGER      NOT NULL DEFAULT 0,
        failed_count    INTEGER      NOT NULL DEFAULT 0,
        quality_report  JSONB
    )
    """)

    # ── states ────────────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE states (
        id    SERIAL       PRIMARY KEY,
        name  VARCHAR(100) NOT NULL UNIQUE,
        code  VARCHAR(10)
    )
    """)

    # ── cities ────────────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE cities (
        id        SERIAL       PRIMARY KEY,
        name      VARCHAR(200) NOT NULL,
        state_id  INTEGER      NOT NULL REFERENCES states(id),
        CONSTRAINT uq_cities_name_state UNIQUE (name, state_id)
    )
    """)

    # ── operators ─────────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE operators (
        id               SERIAL       PRIMARY KEY,
        name             VARCHAR(200) NOT NULL UNIQUE,
        normalized_name  VARCHAR(200) NOT NULL,
        operator_type    VARCHAR(50),
        logo_url         TEXT,
        created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
    """)

    # ── connector_types ───────────────────────────────────────────────────────
    _x("""
    CREATE TABLE connector_types (
        id                   INTEGER PRIMARY KEY,
        connector_name       VARCHAR(100),
        connector_image_url  TEXT
    )
    """)

    # ── amenities ─────────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE amenities (
        id    SERIAL       PRIMARY KEY,
        type  VARCHAR(100) NOT NULL UNIQUE,
        icon  TEXT
    )
    """)

    # ── stations (central fact table) ─────────────────────────────────────────
    _x("""
    CREATE TABLE stations (
        id                        INTEGER      PRIMARY KEY,
        station_name              VARCHAR(500),
        city_id                   INTEGER      REFERENCES cities(id),
        state_id                  INTEGER      REFERENCES states(id),
        operator_id               INTEGER      REFERENCES operators(id),
        city_name_cached          VARCHAR(200),
        operator_name_cached      VARCHAR(200),
        address                   TEXT,
        area                      VARCHAR(500),
        landmark                  VARCHAR(500),
        latitude                  NUMERIC(10,7),
        longitude                 NUMERIC(10,7),
        access_type               VARCHAR(20),
        availability              VARCHAR(30),
        is_connected              BOOLEAN,
        operational_time          VARCHAR(200),
        charger_type              VARCHAR(10),
        highest_power_kw          NUMERIC(8,2),
        avg_rating                NUMERIC(3,2),
        review_count              INTEGER,
        ac_charger_count          INTEGER      NOT NULL DEFAULT 0,
        dc_charger_count          INTEGER      NOT NULL DEFAULT 0,
        total_charger_count       INTEGER      NOT NULL DEFAULT 0,
        total_connector_count     INTEGER      NOT NULL DEFAULT 0,
        available_connector_count INTEGER      NOT NULL DEFAULT 0,
        min_ac_price              NUMERIC(8,2),
        max_ac_price              NUMERIC(8,2),
        min_dc_price              NUMERIC(8,2),
        max_dc_price              NUMERIC(8,2),
        has_amenities             BOOLEAN      NOT NULL DEFAULT FALSE,
        station_image_url         TEXT,
        station_banner            TEXT,
        navigation_link           TEXT,
        search_vector             TSVECTOR,
        scraped_at                VARCHAR(50),
        run_id                    VARCHAR(50)  REFERENCES scrape_runs(run_id)
    )
    """)

    # ── chargers ──────────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE chargers (
        id                        INTEGER      PRIMARY KEY,
        station_id                INTEGER      NOT NULL REFERENCES stations(id),
        charger_name              VARCHAR(200),
        type                      VARCHAR(10),
        power_rating_kw           NUMERIC(8,2),
        price                     NUMERIC(8,2),
        currency                  VARCHAR(10),
        price_display             VARCHAR(100),
        last_used_on              VARCHAR(100),
        connector_count           INTEGER      NOT NULL DEFAULT 0,
        available_connector_count INTEGER      NOT NULL DEFAULT 0
    )
    """)

    # ── connectors ────────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE connectors (
        id                  INTEGER  PRIMARY KEY,
        charger_id          INTEGER  NOT NULL REFERENCES chargers(id),
        station_id          INTEGER  NOT NULL REFERENCES stations(id),
        display_id          INTEGER,
        connector_type      VARCHAR(100),
        connector_type_id   INTEGER  REFERENCES connector_types(id),
        availability        BOOLEAN,
        connector_status    VARCHAR(100),
        error_message       TEXT,
        connector_image     TEXT
    )
    """)

    # ── station_amenities ─────────────────────────────────────────────────────
    _x("""
    CREATE TABLE station_amenities (
        station_id  INTEGER  NOT NULL REFERENCES stations(id),
        amenity_id  INTEGER  NOT NULL REFERENCES amenities(id),
        map_id      INTEGER,
        PRIMARY KEY (station_id, amenity_id)
    )
    """)

    # ── nearby_stations ───────────────────────────────────────────────────────
    _x("""
    CREATE TABLE nearby_stations (
        source_station_id  INTEGER      NOT NULL REFERENCES stations(id),
        nearby_station_id  INTEGER      NOT NULL,
        station_name       VARCHAR(500),
        latitude           NUMERIC(10,7),
        longitude          NUMERIC(10,7),
        access_type        INTEGER,
        avg_review_rating  NUMERIC(3,2),
        is_connected       BOOLEAN,
        station_types      VARCHAR(200),
        branding_logo      TEXT,
        PRIMARY KEY (source_station_id, nearby_station_id)
    )
    """)

    # ── reviews_summary ───────────────────────────────────────────────────────
    _x("""
    CREATE TABLE reviews_summary (
        station_id      INTEGER  PRIMARY KEY REFERENCES stations(id),
        avg_rating      NUMERIC(3,2),
        review_count    INTEGER  NOT NULL DEFAULT 0,
        rating_1_count  INTEGER  NOT NULL DEFAULT 0,
        rating_2_count  INTEGER  NOT NULL DEFAULT 0,
        rating_3_count  INTEGER  NOT NULL DEFAULT 0,
        rating_4_count  INTEGER  NOT NULL DEFAULT 0,
        rating_5_count  INTEGER  NOT NULL DEFAULT 0,
        updated_at      TIMESTAMPTZ
    )
    """)

    # ── station_status_history ────────────────────────────────────────────────
    _x("""
    CREATE TABLE station_status_history (
        id                        BIGSERIAL    PRIMARY KEY,
        station_id                INTEGER      NOT NULL REFERENCES stations(id),
        scrape_run_id             VARCHAR(50)  REFERENCES scrape_runs(run_id),
        availability              VARCHAR(30),
        available_connector_count INTEGER,
        avg_rating                NUMERIC(3,2),
        review_count              INTEGER,
        scraped_at                TIMESTAMPTZ  NOT NULL
    )
    """)

    # ── failed_scrapes ────────────────────────────────────────────────────────
    _x("""
    CREATE TABLE failed_scrapes (
        id             SERIAL      PRIMARY KEY,
        run_id         VARCHAR(50) REFERENCES scrape_runs(run_id),
        station_id     INTEGER     NOT NULL,
        attempt_count  INTEGER     NOT NULL DEFAULT 1,
        last_error     TEXT,
        scraped_at     TIMESTAMPTZ
    )
    """)

    # ── PostGIS: optional spatial column + index ──────────────────────────────
    # If PostGIS is not installed this block is silently skipped.
    # Run migration 0003 after installing PostGIS to add the column retroactively.
    _x("""
    DO $$
    BEGIN
        CREATE EXTENSION IF NOT EXISTS postgis;
        ALTER TABLE stations ADD COLUMN IF NOT EXISTS location GEOGRAPHY(POINT, 4326);
        CREATE INDEX IF NOT EXISTS idx_stations_location ON stations USING GIST (location);
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'PostGIS unavailable — location column skipped (install PostGIS, then run migration 0003)';
    END;
    $$
    """)

    # ── Indexes: stations ─────────────────────────────────────────────────────

    # Core dashboard filters
    _x("CREATE INDEX idx_stations_charger_type ON stations (charger_type)")
    _x("CREATE INDEX idx_stations_availability ON stations (availability)")
    _x("CREATE INDEX idx_stations_access_type  ON stations (access_type)")
    _x("CREATE INDEX idx_stations_city_id      ON stations (city_id)")
    _x("CREATE INDEX idx_stations_state_id     ON stations (state_id)")
    _x("CREATE INDEX idx_stations_operator_id  ON stations (operator_id)")

    # Sort columns
    _x("CREATE INDEX idx_stations_avg_rating   ON stations (avg_rating DESC NULLS LAST)")
    _x("CREATE INDEX idx_stations_min_dc_price ON stations (min_dc_price ASC  NULLS LAST)")
    _x("CREATE INDEX idx_stations_min_ac_price ON stations (min_ac_price ASC  NULLS LAST)")
    _x("CREATE INDEX idx_stations_highest_power ON stations (highest_power_kw DESC NULLS LAST)")

    # Composite: most common combined filter (city + type + availability + rating sort)
    _x("""
    CREATE INDEX idx_stations_filter_core
        ON stations (city_id, charger_type, availability, avg_rating DESC NULLS LAST)
    """)

    # Full-text search (GIN for tsvector, faster reads vs GiST)
    _x("CREATE INDEX idx_stations_search_vector ON stations USING GIN (search_vector)")

    # Autocomplete: trigram index on station_name (supports LIKE '%query%')
    _x("""
    CREATE INDEX idx_stations_name_trgm
        ON stations USING GIN (station_name gin_trgm_ops)
    """)

    # ── Indexes: child tables ─────────────────────────────────────────────────
    _x("CREATE INDEX idx_chargers_station_id  ON chargers   (station_id)")
    _x("CREATE INDEX idx_chargers_type_station ON chargers  (type, station_id)")
    _x("CREATE INDEX idx_connectors_charger_id ON connectors (charger_id)")
    _x("CREATE INDEX idx_connectors_station_id ON connectors (station_id)")
    _x("CREATE INDEX idx_connectors_type_id    ON connectors (connector_type_id)")
    _x("CREATE INDEX idx_nearby_source_id      ON nearby_stations   (source_station_id)")
    _x("CREATE INDEX idx_sa_amenity_id         ON station_amenities (amenity_id)")

    # Status history — will grow large; composite covers uptime trend queries
    _x("CREATE INDEX idx_hist_station_id   ON station_status_history (station_id)")
    _x("CREATE INDEX idx_hist_scraped_at   ON station_status_history (scraped_at DESC)")
    _x("""
    CREATE INDEX idx_hist_station_time
        ON station_status_history (station_id, scraped_at DESC)
    """)

    # ── search_vector trigger ─────────────────────────────────────────────────
    _x("""
    CREATE OR REPLACE FUNCTION update_station_search_vector()
    RETURNS trigger AS $$
    BEGIN
        NEW.search_vector :=
            setweight(to_tsvector('simple', COALESCE(NEW.station_name,         '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(NEW.city_name_cached,     '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(NEW.operator_name_cached, '')), 'C');
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """)

    _x("""
    CREATE TRIGGER trg_station_search_vector
        BEFORE INSERT OR UPDATE OF station_name, city_name_cached, operator_name_cached
        ON stations
        FOR EACH ROW EXECUTE FUNCTION update_station_search_vector()
    """)

    # ── Materialized views ────────────────────────────────────────────────────

    _x("""
    CREATE MATERIALIZED VIEW mv_state_station_distribution AS
    SELECT
        s.id                                                       AS state_id,
        s.name                                                     AS state_name,
        COUNT(st.id)                                               AS total_stations,
        COUNT(st.id) FILTER (WHERE st.availability = 'Available') AS available_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'DC')        AS dc_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'AC')        AS ac_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'Mixed')     AS mixed_stations,
        COALESCE(SUM(st.total_charger_count), 0)                   AS total_chargers,
        COALESCE(SUM(st.ac_charger_count),    0)                   AS ac_charger_count,
        COALESCE(SUM(st.dc_charger_count),    0)                   AS dc_charger_count,
        ROUND(AVG(st.avg_rating) FILTER (WHERE st.avg_rating IS NOT NULL), 2) AS avg_rating
    FROM states s
    LEFT JOIN stations st ON st.state_id = s.id
    GROUP BY s.id, s.name
    WITH DATA
    """)
    _x("""
    CREATE UNIQUE INDEX idx_mv_state_dist_state_id
        ON mv_state_station_distribution (state_id)
    """)

    _x("""
    CREATE MATERIALIZED VIEW mv_city_station_distribution AS
    SELECT
        c.id                                                       AS city_id,
        c.name                                                     AS city_name,
        s.name                                                     AS state_name,
        s.id                                                       AS state_id,
        COUNT(st.id)                                               AS total_stations,
        COUNT(st.id) FILTER (WHERE st.availability = 'Available') AS available_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'DC')        AS dc_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'AC')        AS ac_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'Mixed')     AS mixed_stations,
        COALESCE(SUM(st.total_charger_count), 0)                   AS total_chargers,
        COALESCE(SUM(st.ac_charger_count),    0)                   AS ac_charger_count,
        COALESCE(SUM(st.dc_charger_count),    0)                   AS dc_charger_count,
        ROUND(AVG(st.avg_rating) FILTER (WHERE st.avg_rating IS NOT NULL), 2) AS avg_rating
    FROM cities c
    JOIN  states  s  ON c.state_id = s.id
    LEFT JOIN stations st ON st.city_id = c.id
    GROUP BY c.id, c.name, s.id, s.name
    WITH DATA
    """)
    _x("""
    CREATE UNIQUE INDEX idx_mv_city_dist_city_id
        ON mv_city_station_distribution (city_id)
    """)

    _x("""
    CREATE MATERIALIZED VIEW mv_operator_distribution AS
    SELECT
        o.id                                                       AS operator_id,
        o.name                                                     AS operator_name,
        o.normalized_name,
        o.operator_type,
        COUNT(st.id)                                               AS total_stations,
        COUNT(st.id) FILTER (WHERE st.availability = 'Available') AS available_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'DC')        AS dc_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'AC')        AS ac_stations,
        COUNT(st.id) FILTER (WHERE st.charger_type = 'Mixed')     AS mixed_stations,
        COALESCE(SUM(st.total_charger_count), 0)                   AS total_chargers,
        ROUND(AVG(st.avg_rating) FILTER (WHERE st.avg_rating IS NOT NULL), 2) AS avg_rating
    FROM operators o
    LEFT JOIN stations st ON st.operator_id = o.id
    GROUP BY o.id, o.name, o.normalized_name, o.operator_type
    WITH DATA
    """)
    _x("""
    CREATE UNIQUE INDEX idx_mv_operator_dist_op_id
        ON mv_operator_distribution (operator_id)
    """)

    _x("""
    CREATE MATERIALIZED VIEW mv_charger_speed_distribution AS
    SELECT
        speed_category,
        charger_type,
        COUNT(*)                                      AS charger_count,
        ROUND(AVG(price) FILTER (WHERE price IS NOT NULL), 2) AS avg_price,
        MIN(power_rating_kw)                          AS min_power_kw,
        MAX(power_rating_kw)                          AS max_power_kw
    FROM (
        SELECT
            CASE
                WHEN power_rating_kw < 7.4   THEN 'Slow (<7.4kW)'
                WHEN power_rating_kw < 22    THEN 'Moderate (7.4-22kW)'
                WHEN power_rating_kw < 50    THEN 'Fast (22-50kW)'
                WHEN power_rating_kw < 150   THEN 'Rapid (50-150kW)'
                ELSE                              'Ultra-Rapid (150kW+)'
            END                 AS speed_category,
            type                AS charger_type,
            power_rating_kw,
            price
        FROM chargers
        WHERE power_rating_kw IS NOT NULL
          AND type IS NOT NULL
    ) sub
    GROUP BY speed_category, charger_type
    WITH DATA
    """)
    _x("""
    CREATE UNIQUE INDEX idx_mv_charger_speed_cat
        ON mv_charger_speed_distribution (speed_category, charger_type)
    """)

    _x("""
    CREATE MATERIALIZED VIEW mv_ac_dc_breakdown AS
    SELECT
        'overall'                                                         AS scope,
        COUNT(*) FILTER (WHERE charger_type = 'AC')                      AS ac_stations,
        COUNT(*) FILTER (WHERE charger_type = 'DC')                      AS dc_stations,
        COUNT(*) FILTER (WHERE charger_type = 'Mixed')                   AS mixed_stations,
        COALESCE(SUM(ac_charger_count), 0)                                AS total_ac_chargers,
        COALESCE(SUM(dc_charger_count), 0)                                AS total_dc_chargers,
        ROUND(AVG(min_ac_price) FILTER (WHERE min_ac_price IS NOT NULL), 2) AS avg_min_ac_price,
        ROUND(AVG(min_dc_price) FILTER (WHERE min_dc_price IS NOT NULL), 2) AS avg_min_dc_price,
        ROUND(AVG(highest_power_kw) FILTER (WHERE highest_power_kw IS NOT NULL), 2)
            AS avg_highest_power_kw
    FROM stations
    WITH DATA
    """)
    _x("""
    CREATE UNIQUE INDEX idx_mv_ac_dc_scope
        ON mv_ac_dc_breakdown (scope)
    """)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNGRADE
# ─────────────────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # Materialized views
    _x("DROP MATERIALIZED VIEW IF EXISTS mv_ac_dc_breakdown")
    _x("DROP MATERIALIZED VIEW IF EXISTS mv_charger_speed_distribution")
    _x("DROP MATERIALIZED VIEW IF EXISTS mv_operator_distribution")
    _x("DROP MATERIALIZED VIEW IF EXISTS mv_city_station_distribution")
    _x("DROP MATERIALIZED VIEW IF EXISTS mv_state_station_distribution")

    # Trigger + function
    _x("DROP TRIGGER  IF EXISTS trg_station_search_vector ON stations")
    _x("DROP FUNCTION IF EXISTS update_station_search_vector()")

    # Tables (reverse FK order)
    _x("DROP TABLE IF EXISTS failed_scrapes")
    _x("DROP TABLE IF EXISTS station_status_history")
    _x("DROP TABLE IF EXISTS reviews_summary")
    _x("DROP TABLE IF EXISTS nearby_stations")
    _x("DROP TABLE IF EXISTS station_amenities")
    _x("DROP TABLE IF EXISTS connectors")
    _x("DROP TABLE IF EXISTS chargers")
    _x("DROP TABLE IF EXISTS stations")
    _x("DROP TABLE IF EXISTS amenities")
    _x("DROP TABLE IF EXISTS connector_types")
    _x("DROP TABLE IF EXISTS operators")
    _x("DROP TABLE IF EXISTS cities")
    _x("DROP TABLE IF EXISTS states")
    _x("DROP TABLE IF EXISTS scrape_runs")

    # Extensions (only drop if you own them — skip postgis as it may be shared)
    _x("DROP EXTENSION IF EXISTS pg_trgm")
