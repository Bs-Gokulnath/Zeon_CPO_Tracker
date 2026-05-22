from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import orjson

from scraper.models.station_detail import StationDetailResult
from scraper.parsers.rsc_parser import EXPECTED_FIELDS
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("pipeline.quality_metrics")


@dataclass
class QualityReport:
    run_id: str
    generated_at: str
    total_attempted: int
    parse_success: int
    parse_failed: int
    success_rate_pct: float
    avg_coverage_pct: float
    missing_field_counts: dict[str, int]
    malformed_payload_count: int
    no_chargers_count: int
    missing_coordinates_count: int
    missing_pricing_count: int
    duplicate_station_ids: list[int]
    total_chargers: int
    total_connectors: int
    dc_station_count: int
    ac_station_count: int
    mixed_station_count: int
    coverage_buckets: dict[str, int]
    total_elapsed_seconds: float
    stations_per_second: float


def compute_quality_report(
    results: list[StationDetailResult],
    run_id: str,
    elapsed: float,
) -> QualityReport:
    total = len(results)
    if total == 0:
        return QualityReport(
            run_id=run_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_attempted=0,
            parse_success=0,
            parse_failed=0,
            success_rate_pct=0.0,
            avg_coverage_pct=0.0,
            missing_field_counts={},
            malformed_payload_count=0,
            no_chargers_count=0,
            missing_coordinates_count=0,
            missing_pricing_count=0,
            duplicate_station_ids=[],
            total_chargers=0,
            total_connectors=0,
            dc_station_count=0,
            ac_station_count=0,
            mixed_station_count=0,
            coverage_buckets={"100%": 0, "90-99%": 0, "80-89%": 0, "<80%": 0},
            total_elapsed_seconds=elapsed,
            stations_per_second=0.0,
        )

    successful = [r for r in results if r.parse_success]
    failed = [r for r in results if not r.parse_success]

    # Duplicate IDs
    seen_ids: dict[int, int] = {}
    for r in results:
        seen_ids[r.station_id] = seen_ids.get(r.station_id, 0) + 1
    duplicate_ids = sorted(sid for sid, cnt in seen_ids.items() if cnt > 1)

    # Field-level missing counts
    missing_field_counts: dict[str, int] = {f: 0 for f in EXPECTED_FIELDS}
    coverage_sum = 0.0
    coverage_buckets = {"100%": 0, "90-99%": 0, "80-89%": 0, "<80%": 0}

    no_chargers = 0
    missing_coords = 0
    missing_pricing = 0
    total_chargers = 0
    total_connectors = 0
    dc_count = 0
    ac_count = 0
    mixed_count = 0

    for r in successful:
        coverage_sum += r.coverage_pct
        for f in r.missing_fields:
            if f in missing_field_counts:
                missing_field_counts[f] += 1

        cov = r.coverage_pct
        if cov == 100.0:
            coverage_buckets["100%"] += 1
        elif cov >= 90.0:
            coverage_buckets["90-99%"] += 1
        elif cov >= 80.0:
            coverage_buckets["80-89%"] += 1
        else:
            coverage_buckets["<80%"] += 1

        sd = r.station_detail
        if sd is None:
            continue

        if not sd.plugin_details:
            no_chargers += 1
        if sd.latitude == 0.0 or sd.longitude == 0.0:
            missing_coords += 1

        all_prices = [p.price for p in sd.plugin_details if p.price is not None]
        if sd.plugin_details and not all_prices:
            missing_pricing += 1

        charger_count = len(sd.plugin_details)
        connector_count = sum(len(p.connectors) for p in sd.plugin_details)
        total_chargers += charger_count
        total_connectors += connector_count

        has_dc = any(p.type == "DC" for p in sd.plugin_details)
        has_ac = any(p.type == "AC" for p in sd.plugin_details)
        if has_dc and has_ac:
            mixed_count += 1
        elif has_dc:
            dc_count += 1
        elif has_ac:
            ac_count += 1

    n_success = len(successful)
    avg_cov = coverage_sum / n_success if n_success else 0.0

    return QualityReport(
        run_id=run_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_attempted=total,
        parse_success=n_success,
        parse_failed=len(failed),
        success_rate_pct=round(n_success / total * 100, 2) if total else 0.0,
        avg_coverage_pct=round(avg_cov, 2),
        missing_field_counts=missing_field_counts,
        malformed_payload_count=len(failed),
        no_chargers_count=no_chargers,
        missing_coordinates_count=missing_coords,
        missing_pricing_count=missing_pricing,
        duplicate_station_ids=duplicate_ids,
        total_chargers=total_chargers,
        total_connectors=total_connectors,
        dc_station_count=dc_count,
        ac_station_count=ac_count,
        mixed_station_count=mixed_count,
        coverage_buckets=coverage_buckets,
        total_elapsed_seconds=round(elapsed, 2),
        stations_per_second=round(n_success / elapsed, 2) if elapsed > 0 else 0.0,
    )


def save_quality_report(report: QualityReport, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"full_scrape_report_{report.run_id}.json"
    data = {
        "run_id": report.run_id,
        "generated_at": report.generated_at,
        "total_attempted": report.total_attempted,
        "parse_success": report.parse_success,
        "parse_failed": report.parse_failed,
        "success_rate_pct": report.success_rate_pct,
        "avg_coverage_pct": report.avg_coverage_pct,
        "missing_field_counts": report.missing_field_counts,
        "malformed_payload_count": report.malformed_payload_count,
        "no_chargers_count": report.no_chargers_count,
        "missing_coordinates_count": report.missing_coordinates_count,
        "missing_pricing_count": report.missing_pricing_count,
        "duplicate_station_ids": report.duplicate_station_ids,
        "total_chargers": report.total_chargers,
        "total_connectors": report.total_connectors,
        "dc_station_count": report.dc_station_count,
        "ac_station_count": report.ac_station_count,
        "mixed_station_count": report.mixed_station_count,
        "coverage_buckets": report.coverage_buckets,
        "total_elapsed_seconds": report.total_elapsed_seconds,
        "stations_per_second": report.stations_per_second,
    }
    path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    log.info("Quality report saved -> {p}", p=path)
    return path
