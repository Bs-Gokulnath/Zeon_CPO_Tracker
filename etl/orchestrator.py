from __future__ import annotations

"""
ETL Orchestrator — Step 5B pipeline entry point.

Architecture:
  extract → transform → stage (COPY) → load (upsert) → validate → MV refresh

Usage:
    python -m etl.orchestrator
    python -m etl.orchestrator --run-id 20260521_075852
    python -m etl.orchestrator --dry-run   (extract + transform only, no DB writes)
"""

import asyncio
import sys
import time
from pathlib import Path

import asyncpg
import orjson

from database.refresh_views import MATERIALIZED_VIEWS
from etl.extract import ExtractResult, extract, save_extract_report
from etl.load import (
    LoadCounts,
    load_amenities_dim,
    load_chargers,
    load_cities,
    load_connector_types,
    load_connectors,
    load_failed_scrapes,
    load_nearby_stations,
    load_operators,
    load_reviews_summary,
    load_scrape_run,
    load_states,
    load_station_amenities,
    load_status_history,
    load_stations,
)
from etl.metrics import ETLMetrics, save_etl_metrics
from etl.staging import copy_to_staging, create_staging_tables
from etl.transform import TransformResult, transform
from etl.validators import ValidationReport, save_validation_report, validate_post_load
from scraper.config import settings
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.orchestrator")


def _asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _load_quality_report(run_id: str) -> dict | None:
    path = settings.reports_dir / f"full_scrape_report_{run_id}.json"
    if path.exists():
        return orjson.loads(path.read_bytes())
    return None


def _load_failed_ids(run_id: str) -> dict[str, int]:
    path = settings.failed_data_dir / "failed_station_ids.json"
    if not path.exists():
        return {}
    data = orjson.loads(path.read_bytes())
    if data.get("run_id") == run_id:
        return data.get("failed_ids", {})
    return {}


def _print_report(
    metrics: ETLMetrics,
    counts: LoadCounts,
    validation: ValidationReport | None,
) -> None:
    print()
    print("=" * 60)
    print("ETL PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Run ID         : {metrics.run_id}")
    print()
    print("Phase timings:")
    print(f"  Extract      : {metrics.extract_secs:.2f}s")
    print(f"  Transform    : {metrics.transform_secs:.2f}s")
    print(f"  Staging COPY : {metrics.staging_secs:.2f}s")
    print(f"  Load/upsert  : {metrics.load_secs:.2f}s")
    print(f"  MV refresh   : {metrics.mv_refresh_secs:.2f}s")
    print(f"  Validation   : {metrics.validation_secs:.2f}s")
    print(f"  TOTAL        : {metrics.total_secs:.2f}s")
    print()
    print("Rows loaded:")
    print(f"  States       : {counts.states:,}")
    print(f"  Cities       : {counts.cities:,}")
    print(f"  Operators    : {counts.operators:,}")
    print(f"  Conn. types  : {counts.connector_types:,}")
    print(f"  Amenities    : {counts.amenities:,}")
    print(f"  Stations ins : {counts.stations_inserted:,}")
    print(f"  Stations upd : {counts.stations_updated:,}")
    print(f"  Chargers     : {counts.chargers:,}")
    print(f"  Connectors   : {counts.connectors:,}")
    print(f"  Sta.amenities: {counts.station_amenities:,}")
    print(f"  Nearby       : {counts.nearby:,}")
    print(f"  Reviews      : {counts.reviews:,}")
    print(f"  Hist.records : {counts.history:,}")
    print(f"  Rows/sec     : {metrics.rows_per_sec:,.0f}")
    print()
    if validation:
        status = "PASSED" if validation.passed else "FAILED"
        print(f"Validation     : {status} ({len(validation.issues)} issues)")
        for issue in validation.issues[:10]:
            sev = issue.get("severity", "?")
            chk = issue.get("check", "?")
            cnt = issue.get("count", 0)
            print(f"  [{sev}] {chk}: {cnt:,}")
    print("=" * 60)


async def run(
    run_id: str | None = None,
    dry_run: bool = False,
    final_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> None:
    pipeline_start = time.monotonic()
    final_dir   = final_dir   or settings.final_data_dir
    reports_dir = reports_dir or settings.reports_dir

    metrics = ETLMetrics(run_id=run_id or "pending")

    # ── EXTRACT ───────────────────────────────────────────────────────────────
    log.info("=== EXTRACT ===")
    t0 = time.monotonic()
    extract_result: ExtractResult = extract(final_dir, reports_dir)
    metrics.run_id              = extract_result.run_id
    metrics.extract_secs        = time.monotonic() - t0
    metrics.stations_extracted  = len(extract_result.stations)
    metrics.chargers_extracted  = len(extract_result.chargers)
    metrics.connectors_extracted = len(extract_result.connectors)
    metrics.amenities_extracted  = len(extract_result.amenities)
    metrics.nearby_extracted     = len(extract_result.nearby_stations)
    metrics.extract_errors       = len(extract_result.errors)

    # Use explicit run_id if provided (overrides auto-detected)
    if run_id:
        metrics.run_id = run_id

    save_extract_report(extract_result, reports_dir)

    # ── TRANSFORM ─────────────────────────────────────────────────────────────
    log.info("=== TRANSFORM ===")
    t0 = time.monotonic()
    transform_result: TransformResult = transform(extract_result)
    metrics.transform_secs = time.monotonic() - t0

    if dry_run:
        log.info("DRY RUN — skipping all DB writes")
        print(f"\nDRY RUN complete. Extracted {len(extract_result.stations):,} stations.")
        print(f"Operators detected: {len(transform_result.operators)}")
        print(f"States detected: {len(transform_result.states)}")
        print(f"Cities detected: {len(transform_result.cities)}")
        return

    # ── DB CONNECTION ─────────────────────────────────────────────────────────
    dsn = _asyncpg_dsn(settings.database_url)
    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    counts = LoadCounts()
    validation: ValidationReport | None = None

    try:
        async with pool.acquire() as conn:
            # ── Phase 1: upsert scrape_run record ─────────────────────────────
            quality_report = _load_quality_report(metrics.run_id)
            await load_scrape_run(conn, metrics.run_id, quality_report)

            # ── Phase 2: staging COPY (inside transaction) ────────────────────
            log.info("=== STAGING ===")
            t0 = time.monotonic()
            async with conn.transaction():
                await create_staging_tables(conn)
                await copy_to_staging(
                    conn,
                    stations=transform_result.stations,
                    chargers=transform_result.chargers,
                    connectors=transform_result.connectors,
                    amenities=transform_result.amenities,
                    nearby_stations=transform_result.nearby_stations,
                )
                metrics.staging_secs = time.monotonic() - t0

                # ── Phase 3: load dimensions ───────────────────────────────────
                log.info("=== LOAD DIMENSIONS ===")
                t_load = time.monotonic()
                counts.states           = await load_states(conn)
                counts.cities           = await load_cities(conn)
                counts.operators        = await load_operators(conn)
                counts.connector_types  = await load_connector_types(conn)
                counts.amenities        = await load_amenities_dim(conn)

                # ── Phase 4: load stations ─────────────────────────────────────
                log.info("=== LOAD STATIONS ===")
                ins, upd = await load_stations(conn, metrics.run_id)
                counts.stations_inserted = ins
                counts.stations_updated  = upd
                metrics.stations_inserted = ins
                metrics.stations_updated  = upd
                metrics.stations_skipped  = (
                    metrics.stations_extracted - ins - upd
                )

                # ── Phase 5: load child tables ─────────────────────────────────
                log.info("=== LOAD CHILD TABLES ===")
                counts.chargers          = await load_chargers(conn)
                counts.connectors        = await load_connectors(conn)
                counts.station_amenities = await load_station_amenities(conn)
                counts.nearby            = await load_nearby_stations(conn)
                counts.reviews           = await load_reviews_summary(conn)

                # ── Phase 6: status history (append) ──────────────────────────
                log.info("=== LOAD STATUS HISTORY ===")
                counts.history = await load_status_history(conn, metrics.run_id)
                metrics.history_inserted = counts.history

                # ── Phase 7: failed scrapes ────────────────────────────────────
                failed_ids = _load_failed_ids(metrics.run_id)
                await load_failed_scrapes(conn, metrics.run_id, failed_ids)

                metrics.load_secs = time.monotonic() - t_load

            # Transaction committed. Now refresh MVs outside transaction.
            # ── Phase 8: MV refresh (CONCURRENTLY, outside transaction) ─────────
            # Refresh all 5 MVs in parallel — each gets its own pool connection.
            log.info("=== REFRESH MATERIALIZED VIEWS ===")
            t0 = time.monotonic()

            async def _refresh_one(view_name: str) -> None:
                async with pool.acquire() as c:
                    log.info("Refreshing {v} ...", v=view_name)
                    await c.execute(
                        f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"
                    )

            await asyncio.gather(*[_refresh_one(v) for v in MATERIALIZED_VIEWS])
            metrics.mv_refresh_secs = time.monotonic() - t0

            # ── Phase 9: validation ────────────────────────────────────────────
            log.info("=== VALIDATE ===")
            t0 = time.monotonic()
            validation = await validate_post_load(conn, metrics.run_id)
            metrics.validation_secs = time.monotonic() - t0
            save_validation_report(validation, reports_dir)

    finally:
        await pool.close()

    metrics.total_secs = time.monotonic() - pipeline_start
    metrics.states_upserted          = counts.states
    metrics.cities_upserted          = counts.cities
    metrics.operators_upserted       = counts.operators
    metrics.connector_types_upserted = counts.connector_types
    metrics.amenities_upserted       = counts.amenities
    metrics.chargers_upserted        = counts.chargers
    metrics.connectors_upserted      = counts.connectors
    metrics.station_amenities_upserted = counts.station_amenities
    metrics.nearby_upserted          = counts.nearby
    metrics.reviews_upserted         = counts.reviews

    save_etl_metrics(metrics, reports_dir)
    _print_report(metrics, counts, validation)


def _parse_args(argv: list[str]) -> tuple[str | None, bool]:
    run_id  = None
    dry_run = "--dry-run" in argv
    if "--run-id" in argv:
        idx = argv.index("--run-id")
        if idx + 1 < len(argv):
            run_id = argv[idx + 1]
    return run_id, dry_run


def main() -> None:
    run_id, dry_run = _parse_args(sys.argv[1:])
    asyncio.run(run(run_id=run_id, dry_run=dry_run))


if __name__ == "__main__":
    main()
