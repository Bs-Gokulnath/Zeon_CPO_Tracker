"""
Station list collector — Step 3 of the Statiq scraping pipeline.

Fetches all EV charging stations in India from the Statiq markers API in a
single POST request, validates and deduplicates the response, then persists
three artefacts:

  data/raw/markers_<timestamp>.json        — full API envelope
  data/processed/stations_<timestamp>.json — cleaned array of station objects
  data/exports/stations.csv               — flat CSV (+ timestamped backup)

Usage (CLI):
    python -m scraper.collectors.station_list

Usage (library):
    result = asyncio.run(collect_station_list())
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from scraper.config import settings
from scraper.http.client import AsyncHTTPClient
from scraper.parsers.schemas import MarkersAPIResponse, StationMarker
from scraper.utils.file_writer import save_cleaned_json, save_csv, save_raw_json
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("collectors.station_list")

_MIN_EXPECTED_STATIONS = 6_000


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CollectionResult:
    stations: list[StationMarker]

    # Quality metrics
    total_raw: int = 0
    duplicates_removed: int = 0
    zero_coord_count: int = 0
    null_address_count: int = 0
    public_count: int = 0
    private_count: int = 0

    # File paths
    raw_json_path: str = ""
    cleaned_json_path: str = ""
    csv_path: str = ""

    # Timing
    elapsed_seconds: float = 0.0

    @property
    def station_count(self) -> int:
        return len(self.stations)

    def summary(self) -> str:
        lines = [
            f"Stations collected : {self.station_count:,}",
            f"Duplicates removed : {self.duplicates_removed:,}",
            f"Zero coordinates   : {self.zero_coord_count:,}",
            f"Null addresses     : {self.null_address_count:,}",
            f"Public / Private   : {self.public_count:,} / {self.private_count:,}",
            f"Elapsed            : {self.elapsed_seconds:.1f}s",
            f"Raw JSON           : {self.raw_json_path}",
            f"Cleaned JSON       : {self.cleaned_json_path}",
            f"CSV export         : {self.csv_path}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Core collector
# ─────────────────────────────────────────────────────────────────────────────

async def collect_station_list() -> CollectionResult:
    """
    Fetch all India stations, validate, deduplicate, persist, and return stats.

    Raises
    ------
    RuntimeError
        If the API returns fewer than _MIN_EXPECTED_STATIONS stations (data
        integrity guard — likely a partial response or geography error).
    """
    t0 = time.monotonic()
    result = CollectionResult(stations=[])

    payload = _build_markers_payload()

    log.info("Fetching station markers (India bbox, {n} polygon vertices)", n=len(settings.india_bbox_vertices))

    async with AsyncHTTPClient(read_timeout=settings.scraper_markers_timeout) as client:
        raw: dict[str, Any] = await client.post_json(settings.statiq_markers_url, payload)

    log.info("Markers API responded — parsing response…")

    # ── Persist raw response before any further processing ────────────────────
    raw_path = save_raw_json(raw, settings.raw_data_dir, "markers")
    result.raw_json_path = str(raw_path)

    # ── Validate via Pydantic ─────────────────────────────────────────────────
    api_response = MarkersAPIResponse.model_validate(raw)
    raw_stations = api_response.stations
    result.total_raw = len(raw_stations)

    log.info("Parsed {n} raw station records", n=result.total_raw)

    # ── Deduplicate by station_id ─────────────────────────────────────────────
    seen: set[int] = set()
    unique: list[StationMarker] = []
    for s in raw_stations:
        if s.station_id in seen:
            result.duplicates_removed += 1
        else:
            seen.add(s.station_id)
            unique.append(s)

    if result.duplicates_removed:
        log.warning(
            "Removed {n} duplicate station_ids from response",
            n=result.duplicates_removed,
        )

    result.stations = unique

    # ── Quality metrics ───────────────────────────────────────────────────────
    for s in unique:
        if not s.has_valid_coordinates:
            result.zero_coord_count += 1
        if s.address is None:
            result.null_address_count += 1
        if s.is_public:
            result.public_count += 1
        else:
            result.private_count += 1

    _log_quality_report(result)

    # ── Integrity guard ───────────────────────────────────────────────────────
    if result.station_count < _MIN_EXPECTED_STATIONS:
        raise RuntimeError(
            f"Only {result.station_count} stations returned — expected ≥ "
            f"{_MIN_EXPECTED_STATIONS}. Possible partial response or wrong bbox."
        )

    # ── Persist cleaned data ──────────────────────────────────────────────────
    records = _to_records(unique)

    cleaned_path = save_cleaned_json(records, settings.processed_data_dir, "stations")
    result.cleaned_json_path = str(cleaned_path)

    csv_path = save_csv(records, settings.exports_dir / "stations.csv")
    result.csv_path = str(csv_path)

    result.elapsed_seconds = time.monotonic() - t0

    log.info(
        "Station list collection complete in {t:.1f}s — {n} stations",
        t=result.elapsed_seconds,
        n=result.station_count,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_markers_payload() -> dict[str, Any]:
    """Build the POST body for the /station/v1/markers endpoint.

    The API requires a centroid point (latitude/longitude) plus the bounding
    polygon vertices. Country is no longer a valid field as of 2026-05.
    India centroid: 20.5937°N, 78.9629°E
    """
    return {
        "latitude": 20.5937,
        "longitude": 78.9629,
        "vertices": settings.india_bbox_vertices,
    }


def _to_records(stations: list[StationMarker]) -> list[dict[str, Any]]:
    """Serialise StationMarker list to plain dicts for file output."""
    return [
        {
            "station_id": s.station_id,
            "station_name": s.station_name,
            "address": s.address,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "access_type": s.access_type,
            "is_community_listed": s.is_community_listed,
            "map_pin_url": s.map_pin_url,
            "focused_map_pin_url": s.focused_map_pin_url,
        }
        for s in stations
    ]


def _log_quality_report(result: CollectionResult) -> None:
    log.info(
        "Quality report — public={pub} private={priv} zero_coords={zc} null_addr={na}",
        pub=result.public_count,
        priv=result.private_count,
        zc=result.zero_coord_count,
        na=result.null_address_count,
    )
    if result.zero_coord_count:
        log.warning(
            "{n} stations have zero coordinates (lat=0 lon=0) — likely data errors",
            n=result.zero_coord_count,
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    result = asyncio.run(collect_station_list())
    print("\n" + "═" * 50)
    print("COLLECTION COMPLETE")
    print("═" * 50)
    print(result.summary())
    print("═" * 50)


if __name__ == "__main__":
    main()
