from __future__ import annotations

"""
Post-load validation: run integrity checks against the production tables
and produce an etl_validation_report.json.
"""

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import asyncpg
import orjson

from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.validators")


@dataclass
class ValidationReport:
    run_id: str
    elapsed_secs: float = 0.0
    passed: bool = True
    # Row counts
    total_stations: int = 0
    total_chargers: int = 0
    total_connectors: int = 0
    total_nearby: int = 0
    total_reviews: int = 0
    total_history: int = 0
    # Issues
    orphan_chargers: int = 0            # charger.station_id not in stations
    orphan_connectors: int = 0          # connector.charger_id not in chargers
    invalid_coordinates: int = 0        # lat/lon outside India bounds
    duplicate_station_ids: int = 0
    stations_missing_operator: int = 0  # operator_id IS NULL
    stations_missing_city: int = 0      # city_id IS NULL
    stations_missing_state: int = 0     # state_id IS NULL
    stations_zero_chargers: int = 0     # total_charger_count = 0
    connectors_null_type: int = 0       # connector_type IS NULL
    issues: list[dict] = field(default_factory=list)


async def validate_post_load(
    conn: asyncpg.Connection,
    run_id: str,
) -> ValidationReport:
    t0 = time.monotonic()
    report = ValidationReport(run_id=run_id)

    # ── Row counts ────────────────────────────────────────────────────────────
    report.total_stations   = await conn.fetchval("SELECT COUNT(*) FROM stations")
    report.total_chargers   = await conn.fetchval("SELECT COUNT(*) FROM chargers")
    report.total_connectors = await conn.fetchval("SELECT COUNT(*) FROM connectors")
    report.total_nearby     = await conn.fetchval("SELECT COUNT(*) FROM nearby_stations")
    report.total_reviews    = await conn.fetchval("SELECT COUNT(*) FROM reviews_summary")
    report.total_history    = await conn.fetchval(
        "SELECT COUNT(*) FROM station_status_history WHERE scrape_run_id = $1", run_id
    )

    # ── Orphan detection ──────────────────────────────────────────────────────
    report.orphan_chargers = await conn.fetchval("""
        SELECT COUNT(*) FROM chargers c
        WHERE NOT EXISTS (SELECT 1 FROM stations s WHERE s.id = c.station_id)
    """)
    if report.orphan_chargers:
        report.issues.append({
            "severity": "ERROR",
            "check": "orphan_chargers",
            "count": report.orphan_chargers,
            "detail": "chargers.station_id has no matching station",
        })
        report.passed = False

    report.orphan_connectors = await conn.fetchval("""
        SELECT COUNT(*) FROM connectors co
        WHERE NOT EXISTS (SELECT 1 FROM chargers c WHERE c.id = co.charger_id)
    """)
    if report.orphan_connectors:
        report.issues.append({
            "severity": "ERROR",
            "check": "orphan_connectors",
            "count": report.orphan_connectors,
            "detail": "connectors.charger_id has no matching charger",
        })
        report.passed = False

    # ── Coordinate validity ───────────────────────────────────────────────────
    report.invalid_coordinates = await conn.fetchval("""
        SELECT COUNT(*) FROM stations
        WHERE latitude IS NOT NULL
          AND (latitude  NOT BETWEEN 6.0  AND 37.5
            OR longitude NOT BETWEEN 68.0 AND 97.5)
    """)
    if report.invalid_coordinates:
        report.issues.append({
            "severity": "WARNING",
            "check": "invalid_coordinates",
            "count": report.invalid_coordinates,
            "detail": "station lat/lon outside India bounding box",
        })

    # ── Duplicate station IDs ─────────────────────────────────────────────────
    report.duplicate_station_ids = await conn.fetchval("""
        SELECT COUNT(*) FROM (
            SELECT id FROM stations GROUP BY id HAVING COUNT(*) > 1
        ) dupes
    """)
    if report.duplicate_station_ids:
        report.issues.append({
            "severity": "ERROR",
            "check": "duplicate_station_ids",
            "count": report.duplicate_station_ids,
            "detail": "station IDs are not unique",
        })
        report.passed = False

    # ── Missing FK resolutions ────────────────────────────────────────────────
    report.stations_missing_operator = await conn.fetchval(
        "SELECT COUNT(*) FROM stations WHERE operator_id IS NULL"
    )
    report.stations_missing_city = await conn.fetchval(
        "SELECT COUNT(*) FROM stations WHERE city_id IS NULL"
    )
    report.stations_missing_state = await conn.fetchval(
        "SELECT COUNT(*) FROM stations WHERE state_id IS NULL"
    )
    for field_name, count, label in [
        ("stations_missing_operator", report.stations_missing_operator, "operator_id"),
        ("stations_missing_city",     report.stations_missing_city,     "city_id"),
        ("stations_missing_state",    report.stations_missing_state,    "state_id"),
    ]:
        if count:
            pct = count / report.total_stations * 100 if report.total_stations else 0
            report.issues.append({
                "severity": "WARNING",
                "check": f"stations_missing_{label.replace('_id','')}",
                "count": count,
                "pct": round(pct, 1),
                "detail": f"stations with NULL {label}",
            })

    # ── Zero-charger stations ─────────────────────────────────────────────────
    report.stations_zero_chargers = await conn.fetchval(
        "SELECT COUNT(*) FROM stations WHERE total_charger_count = 0"
    )
    if report.stations_zero_chargers:
        report.issues.append({
            "severity": "WARNING",
            "check": "stations_zero_chargers",
            "count": report.stations_zero_chargers,
            "detail": "stations with total_charger_count = 0",
        })

    # ── Connector type nulls ──────────────────────────────────────────────────
    report.connectors_null_type = await conn.fetchval(
        "SELECT COUNT(*) FROM connectors WHERE connector_type IS NULL"
    )
    if report.connectors_null_type:
        report.issues.append({
            "severity": "INFO",
            "check": "connectors_null_type",
            "count": report.connectors_null_type,
            "detail": "connectors missing connector_type string",
        })

    report.elapsed_secs = time.monotonic() - t0
    status = "PASSED" if report.passed else "FAILED"
    log.info(
        "Validation {status} in {t:.2f}s — {n} issues",
        status=status, t=report.elapsed_secs, n=len(report.issues),
    )
    return report


def save_validation_report(report: ValidationReport, reports_dir: Path) -> Path:
    path = reports_dir / f"etl_validation_report_{report.run_id}.json"
    path.write_bytes(orjson.dumps(asdict(report), option=orjson.OPT_INDENT_2))
    log.info("Validation report saved -> {p}", p=path)
    return path
