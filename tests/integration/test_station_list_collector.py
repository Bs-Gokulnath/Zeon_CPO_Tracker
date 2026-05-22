"""
Integration test for the station list collector.

Makes a LIVE call to the Statiq markers API.
Run with:  pytest tests/integration/ -v -m integration

Marked `integration` so the CI unit-test suite can exclude it with:
  pytest -m "not integration"
"""
from __future__ import annotations

import pytest

from scraper.collectors.station_list import CollectionResult, collect_station_list

pytestmark = pytest.mark.integration

_MIN_STATIONS = 6_000


@pytest.mark.asyncio
async def test_collect_station_list_live():
    """Full end-to-end: fetch → validate → deduplicate → persist."""
    result: CollectionResult = await collect_station_list()

    # Station count integrity
    assert result.station_count >= _MIN_STATIONS, (
        f"Expected ≥ {_MIN_STATIONS} stations, got {result.station_count}"
    )

    # No unexpected mass-duplication
    assert result.duplicates_removed < result.total_raw * 0.05, (
        f"Too many duplicates: {result.duplicates_removed} / {result.total_raw}"
    )

    # At least 80% should have valid (non-zero) coordinates
    valid_coords = result.station_count - result.zero_coord_count
    assert valid_coords >= result.station_count * 0.80, (
        f"Too many zero-coordinate stations: {result.zero_coord_count}"
    )

    # Access type breakdown sanity — at least some public stations
    assert result.public_count > 0, "Expected at least one public station"

    # File paths were written
    assert result.raw_json_path, "raw_json_path should not be empty"
    assert result.cleaned_json_path, "cleaned_json_path should not be empty"
    assert result.csv_path, "csv_path should not be empty"

    # Timing — should complete within 120s even on slow connections
    assert result.elapsed_seconds < 120, (
        f"Collection took too long: {result.elapsed_seconds:.1f}s"
    )

    # Spot-check first station has required fields
    first = result.stations[0]
    assert first.station_id > 0
    assert first.station_name.strip() == first.station_name
    assert first.latitude != 0.0 or first.longitude != 0.0
