from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import orjson
import pandas as pd

from scraper.config import settings
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.extract")

# Column renames: normalizer names → DB column names
_STATION_RENAMES = {"station_id": "id", "city": "city_name"}
_CHARGER_RENAMES = {"charger_id": "id"}
_CONNECTOR_RENAMES = {"connector_id": "id"}

# Coordinate validity bounds
_LAT_MIN, _LAT_MAX = 6.0, 37.5   # India's latitude range (with margin)
_LON_MIN, _LON_MAX = 68.0, 97.5  # India's longitude range (with margin)


@dataclass
class ExtractResult:
    stations: pd.DataFrame
    chargers: pd.DataFrame
    connectors: pd.DataFrame
    amenities: pd.DataFrame
    nearby_stations: pd.DataFrame
    connector_types: pd.DataFrame
    run_id: str
    elapsed_secs: float
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


def _load_json(path: Path, name: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{name} not found at {path}")
    data = orjson.loads(path.read_bytes())
    log.info("Loaded {name}: {n} records from {p}", name=name, n=len(data), p=path)
    return data


def _find_run_id(final_dir: Path, reports_dir: Path) -> str:
    """
    Resolve run_id from the latest quality report, falling back to a timestamp.
    """
    reports = sorted(reports_dir.glob("full_scrape_report_*.json"), key=lambda p: p.stat().st_mtime)
    if reports:
        stem = reports[-1].stem  # full_scrape_report_20260521_075852
        return stem.replace("full_scrape_report_", "")
    return "unknown"


def _validate_stations(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []

    initial_count = len(df)

    # Drop rows missing required ID
    missing_id = df["id"].isna()
    if missing_id.any():
        errors.append({"type": "missing_id", "count": int(missing_id.sum())})
        df = df[~missing_id]

    # Duplicate station IDs
    dupes = df.duplicated(subset=["id"], keep="first")
    if dupes.any():
        warnings.append({"type": "duplicate_station_id", "count": int(dupes.sum())})
        df = df[~dupes]

    # Coordinate range check
    if "latitude" in df.columns and "longitude" in df.columns:
        lat_ok = df["latitude"].between(_LAT_MIN, _LAT_MAX) | df["latitude"].isna()
        lon_ok = df["longitude"].between(_LON_MIN, _LON_MAX) | df["longitude"].isna()
        bad_coords = ~(lat_ok & lon_ok)
        if bad_coords.any():
            warnings.append({"type": "invalid_coordinates", "count": int(bad_coords.sum())})

    # Type coercions
    df["id"] = df["id"].astype(int)
    for col in ("review_count", "ac_charger_count", "dc_charger_count",
                "total_charger_count", "total_connector_count", "available_connector_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ("avg_rating", "highest_power_kw", "latitude", "longitude",
                "min_ac_price", "max_ac_price", "min_dc_price", "max_dc_price"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    log.info(
        "Stations validated: {final}/{initial} kept ({err} errors, {warn} warnings)",
        final=len(df), initial=initial_count, err=len(errors), warn=len(warnings),
    )
    return df, errors, warnings


def _validate_chargers(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    errors: list[dict] = []
    dupes = df.duplicated(subset=["id"], keep="first")
    if dupes.any():
        errors.append({"type": "duplicate_charger_id", "count": int(dupes.sum())})
        df = df[~dupes]
    df["id"] = pd.to_numeric(df["id"], errors="coerce").dropna().astype(int)
    df["station_id"] = pd.to_numeric(df["station_id"], errors="coerce").astype(int)
    df["power_rating_kw"] = pd.to_numeric(df.get("power_rating_kw"), errors="coerce")
    df["price"] = pd.to_numeric(df.get("price"), errors="coerce")
    return df, errors


def _validate_connectors(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    errors: list[dict] = []
    dupes = df.duplicated(subset=["id"], keep="first")
    if dupes.any():
        errors.append({"type": "duplicate_connector_id", "count": int(dupes.sum())})
        df = df[~dupes]
    df["id"] = pd.to_numeric(df["id"], errors="coerce").dropna().astype(int)
    df["charger_id"] = pd.to_numeric(df["charger_id"], errors="coerce").astype(int)
    df["station_id"] = pd.to_numeric(df["station_id"], errors="coerce").astype(int)
    if "availability" in df.columns:
        df["availability"] = df["availability"].map({True: True, False: False, 1: True, 0: False})
    return df, errors


def extract(
    final_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> ExtractResult:
    t0 = time.monotonic()
    final_dir = final_dir or settings.final_data_dir
    reports_dir = reports_dir or settings.reports_dir
    all_errors: list[dict] = []
    all_warnings: list[dict] = []

    run_id = _find_run_id(final_dir, reports_dir)
    log.info("Extracting data for run_id={rid}", rid=run_id)

    # ── Load raw JSON ─────────────────────────────────────────────────────────
    raw_stations        = _load_json(final_dir / "stations.json",        "stations")
    raw_chargers        = _load_json(final_dir / "chargers.json",        "chargers")
    raw_connectors      = _load_json(final_dir / "connectors.json",      "connectors")
    raw_amenities       = _load_json(final_dir / "amenities.json",       "amenities")
    raw_nearby          = _load_json(final_dir / "nearby_stations.json", "nearby_stations")

    # connector_types may not always exist
    ct_path = final_dir / "connector_types.json"
    raw_connector_types = _load_json(ct_path, "connector_types") if ct_path.exists() else []

    # ── Build DataFrames ──────────────────────────────────────────────────────
    stations_df = pd.DataFrame(raw_stations).rename(columns=_STATION_RENAMES)
    chargers_df = pd.DataFrame(raw_chargers).rename(columns=_CHARGER_RENAMES)
    connectors_df = pd.DataFrame(raw_connectors).rename(columns=_CONNECTOR_RENAMES)
    amenities_df = pd.DataFrame(raw_amenities) if raw_amenities else pd.DataFrame()
    nearby_df = pd.DataFrame(raw_nearby) if raw_nearby else pd.DataFrame()
    connector_types_df = pd.DataFrame(raw_connector_types) if raw_connector_types else pd.DataFrame()

    # ── Validate ──────────────────────────────────────────────────────────────
    stations_df, st_err, st_warn = _validate_stations(stations_df)
    all_errors.extend(st_err)
    all_warnings.extend(st_warn)

    chargers_df, ch_err = _validate_chargers(chargers_df)
    all_errors.extend(ch_err)

    connectors_df, co_err = _validate_connectors(connectors_df)
    all_errors.extend(co_err)

    elapsed = time.monotonic() - t0
    log.info(
        "Extract complete in {t:.2f}s — stations={s} chargers={c} connectors={co} "
        "amenities={a} nearby={n} errors={e}",
        t=elapsed, s=len(stations_df), c=len(chargers_df), co=len(connectors_df),
        a=len(amenities_df), n=len(nearby_df), e=len(all_errors),
    )

    return ExtractResult(
        stations=stations_df,
        chargers=chargers_df,
        connectors=connectors_df,
        amenities=amenities_df,
        nearby_stations=nearby_df,
        connector_types=connector_types_df,
        run_id=run_id,
        elapsed_secs=elapsed,
        errors=all_errors,
        warnings=all_warnings,
    )


def save_extract_report(result: ExtractResult, reports_dir: Path) -> Path:
    report = {
        "run_id": result.run_id,
        "elapsed_secs": result.elapsed_secs,
        "row_counts": {
            "stations": len(result.stations),
            "chargers": len(result.chargers),
            "connectors": len(result.connectors),
            "amenities": len(result.amenities),
            "nearby_stations": len(result.nearby_stations),
            "connector_types": len(result.connector_types),
        },
        "errors": result.errors,
        "warnings": result.warnings,
    }
    path = reports_dir / f"extract_report_{result.run_id}.json"
    path.write_bytes(orjson.dumps(report, option=orjson.OPT_INDENT_2))
    return path
