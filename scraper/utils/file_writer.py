"""
File persistence utilities for the scraper.

All I/O is synchronous (called after async data collection completes).
Uses orjson for fast serialisation and pandas for CSV export.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
import pandas as pd

from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("file_writer")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────────────────────────────────────
# JSON writers
# ─────────────────────────────────────────────────────────────────────────────

def save_raw_json(data: Any, directory: Path, stem: str) -> Path:
    """
    Serialize *data* to JSON and write it to *directory/{stem}_{timestamp}.json*.

    Uses orjson for speed (handles datetime, Path, Pydantic models).
    The raw file preserves the full API response envelope (meta + data).

    Returns the Path of the written file.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}_{_timestamp()}.json"

    serialised = orjson.dumps(
        data,
        option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
    )
    path.write_bytes(serialised)
    log.info("Saved raw JSON → {path} ({size} bytes)", path=path, size=len(serialised))
    return path


def save_cleaned_json(records: list[dict[str, Any]], directory: Path, stem: str) -> Path:
    """
    Write a cleaned list of dicts to *directory/{stem}_{timestamp}.json*.

    The cleaned file is an array of station objects (no API envelope).
    Includes a header with record count and generation timestamp.

    Returns the Path of the written file.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}_{_timestamp()}.json"

    payload = {
        "generated_at": datetime.now().isoformat(),
        "record_count": len(records),
        "records": records,
    }
    serialised = orjson.dumps(
        payload,
        option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
    )
    path.write_bytes(serialised)
    log.info(
        "Saved cleaned JSON → {path} ({n} records, {size} bytes)",
        path=path,
        n=len(records),
        size=len(serialised),
    )
    return path


# ─────────────────────────────────────────────────────────────────────────────
# CSV export
# ─────────────────────────────────────────────────────────────────────────────

# Column order for the CSV — explicit so it's stable across runs
_CSV_COLUMNS = [
    "station_id",
    "station_name",
    "address",
    "latitude",
    "longitude",
    "access_type",
    "is_community_listed",
    "map_pin_url",
    "focused_map_pin_url",
]


def save_csv(records: list[dict[str, Any]], path: Path) -> Path:
    """
    Write *records* to a CSV file at *path*.

    Always overwrites (no timestamp in filename — this is the "latest" export
    that external tools consume). A timestamped backup copy is also written
    alongside it for audit purposes.

    Returns the Path of the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(records)

    # Reorder to canonical column order; add any extra columns at the end
    present = [c for c in _CSV_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in _CSV_COLUMNS]
    df = df[present + extras]

    df.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compat

    # Timestamped backup
    backup_path = path.parent / f"stations_{_timestamp()}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")

    log.info(
        "Saved CSV → {path} ({n} rows, {cols} cols)",
        path=path,
        n=len(df),
        cols=len(df.columns),
    )
    log.debug("CSV backup → {path}", path=backup_path)
    return path
