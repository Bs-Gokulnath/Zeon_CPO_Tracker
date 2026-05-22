from __future__ import annotations

import re
from datetime import datetime, timezone

from scraper.models.station_detail import (
    NearbyData,
    NearbyStation,
    StationDetail,
    StationDetailResult,
)
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("parsers.rsc_parser")

EXPECTED_FIELDS: list[str] = [
    "station_name",
    "latitude",
    "longitude",
    "address",
    "area",
    "operational_time",
    "connector_types",
    "avg_review_rating",
    "no_of_reviews",
    "station_image_url",
    "is_connected",
    "landmark",
    "amenities_icon",
    "plugin_details",
    "review_stats",
    "station_city_name",
    "station_access_type",
    "availability",
    "highest_power_rating",
    "charger_type_of_station",
    "closing_status",
    "navigation_link",
]


class RSCParseError(Exception):
    pass


def _extract_json_object(text: str, start: int) -> dict:
    """
    Extract a balanced JSON object from *text* starting at the `{` at *start*.

    Uses a character-by-character state machine to handle string literals
    correctly, so braces inside quoted strings are not counted.
    """
    depth = 0
    in_string = False
    i = start

    while i < len(text):
        ch = text[i]

        if in_string:
            if ch == "\\" :
                i += 2
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    import orjson
                    return orjson.loads(text[start : i + 1])
        i += 1

    raise RSCParseError(f"Unbalanced braces in JSON object starting at position {start}")


def parse_rsc_payload(text: str) -> dict:
    """
    Parse a raw RSC `text/x-component` payload and return the `stationData` dict.

    Primary strategy: scan newline-delimited lines for the one containing both
    `"stationData":` and `"station_name"`, then extract the balanced JSON value.

    Fallback strategy: regex search across the full text with DOTALL, then
    extract via the same brace-balanced extractor.
    """
    for line in text.split("\n"):
        if '"stationData":' in line and '"station_name"' in line:
            key_pos = line.find('"stationData":')
            value_start = line.find("{", key_pos + len('"stationData":'))
            if value_start != -1:
                try:
                    return _extract_json_object(line, value_start)
                except Exception as exc:
                    log.debug("Primary line extraction failed, will try fallback: {e}", e=exc)

    match = re.search(r'"stationData"\s*:\s*(\{)', text, re.DOTALL)
    if match:
        try:
            return _extract_json_object(text, match.start(1))
        except Exception as exc:
            raise RSCParseError(f"Fallback extraction failed: {exc}") from exc

    raise RSCParseError("stationData not found in RSC payload")


def _compute_missing_fields(detail: StationDetail) -> list[str]:
    missing: list[str] = []
    for field_name in EXPECTED_FIELDS:
        value = getattr(detail, field_name, None)
        if value is None:
            missing.append(field_name)
        elif isinstance(value, list) and len(value) == 0:
            # Empty lists on fields that should have content are considered missing
            if field_name in {"connector_types", "plugin_details", "amenities_icon"}:
                missing.append(field_name)
    return missing


def extract_station_detail_result(text: str, station_id: int) -> StationDetailResult:
    """
    Parse *text* (RSC payload) for *station_id* and return a fully populated
    `StationDetailResult`, including coverage metrics.

    On any parse failure, returns a result with `parse_success=False`.
    """
    scraped_at = datetime.now(timezone.utc).isoformat()

    try:
        raw_station_data = parse_rsc_payload(text)
    except RSCParseError as exc:
        log.error(
            "RSC parse failed for station {sid}: {e}",
            sid=station_id,
            e=exc,
        )
        return StationDetailResult(
            station_id=station_id,
            scraped_at=scraped_at,
            parse_success=False,
        )

    try:
        detail = StationDetail.model_validate(raw_station_data["data"])
    except Exception as exc:
        log.error(
            "StationDetail validation failed for station {sid}: {e}",
            sid=station_id,
            e=exc,
        )
        return StationDetailResult(
            station_id=station_id,
            scraped_at=scraped_at,
            parse_success=False,
        )

    nearby_stations: list[NearbyStation] = []
    try:
        nearby_raw = raw_station_data.get("nearByData", {})
        cards_raw = nearby_raw.get("data", {}).get("cards", [])
        if cards_raw:
            nearby_data = NearbyData(cards=[NearbyStation.model_validate(c) for c in cards_raw])
            nearby_stations = nearby_data.cards
    except Exception as exc:
        log.warning(
            "NearbyData parse failed for station {sid} (non-fatal): {e}",
            sid=station_id,
            e=exc,
        )

    missing_fields = _compute_missing_fields(detail)
    coverage_pct = (len(EXPECTED_FIELDS) - len(missing_fields)) / len(EXPECTED_FIELDS) * 100

    return StationDetailResult(
        station_id=station_id,
        station_detail=detail,
        nearby_stations=nearby_stations,
        ac_count=raw_station_data.get("acCount", 0),
        dc_count=raw_station_data.get("dcCount", 0),
        ac_prices=raw_station_data.get("acPrices") or [],
        dc_prices=raw_station_data.get("dcPrices") or [],
        scraped_at=scraped_at,
        parse_success=True,
        missing_fields=missing_fields,
        coverage_pct=round(coverage_pct, 1),
    )
