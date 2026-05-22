"""
Admin route — scrape trigger, status, and history.
POST /admin/scrape/trigger  → launches full_scrape + etl.orchestrator as subprocesses
GET  /admin/scrape/status   → current job state (polled by frontend)
GET  /admin/scrape/history  → list of past runs with before/after diff
"""
from __future__ import annotations

import asyncio
import datetime
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import orjson
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import engine

router = APIRouter(prefix="/admin", tags=["admin"])

_ANSI         = re.compile(r"\x1b\[[0-9;]*m")
_HISTORY_FILE = Path("data/scrape_history.json")

_job: dict[str, Any] = {
    "phase":    "idle",
    "message":  "",
    "elapsed_secs": 0,
    "stations_scraped": 0,
    "stations_loaded":  0,
    "error":    None,
}
_start_mono: float | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean(line: str) -> str:
    return _ANSI.sub("", line).strip()


async def _snapshot_stats() -> dict:
    """Query live DB for current overview numbers."""
    try:
        async with AsyncSession(engine) as session:
            row = await session.execute(text("""
                SELECT
                    COUNT(*)                                                                AS total_stations,
                    COUNT(*) FILTER (WHERE availability = 'Available')                     AS available_stations,
                    COALESCE(SUM(total_charger_count),   0)                                AS total_chargers,
                    COALESCE(SUM(total_connector_count), 0)                                AS total_connectors,
                    COUNT(DISTINCT city_id)                                                AS cities_covered,
                    COUNT(DISTINCT operator_id) FILTER (WHERE operator_id IS NOT NULL)     AS operators_count
                FROM stations
            """))
            r = row.first()
            return {k: int(v) for k, v in dict(r._mapping).items()} if r else {}
    except Exception:
        return {}


def _load_history() -> list[dict]:
    if not _HISTORY_FILE.exists():
        return []
    try:
        return orjson.loads(_HISTORY_FILE.read_bytes())
    except Exception:
        return []


def _save_history(runs: list[dict]) -> None:
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_bytes(orjson.dumps(runs, option=orjson.OPT_INDENT_2))


def _append_run(entry: dict) -> None:
    runs = _load_history()
    runs.insert(0, entry)      # newest first
    _save_history(runs[:50])   # keep last 50 runs


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/scrape/status")
async def scrape_status() -> dict:
    result = dict(_job)
    result["elapsed_secs"] = int(time.monotonic() - _start_mono) if _start_mono else 0
    return result


@router.get("/scrape/history")
async def scrape_history() -> list[dict]:
    return _load_history()


@router.post("/scrape/trigger")
async def scrape_trigger() -> dict:
    global _job, _start_mono

    if _job["phase"] in ("scraping", "loading"):
        return {"ok": False, "message": f"Already running: {_job['phase']}"}

    _start_mono = time.monotonic()
    _job = {
        "phase":    "scraping",
        "message":  "Starting scrape…",
        "elapsed_secs": 0,
        "stations_scraped": 0,
        "stations_loaded":  0,
        "error":    None,
    }

    asyncio.create_task(_run_pipeline())
    return {"ok": True}


# ── Background pipeline ───────────────────────────────────────────────────────

async def _run_subprocess(args: list[str], phase_label: str, progress_key: str) -> bool:
    global _job

    _job["phase"]   = phase_label
    _job["message"] = f"{phase_label.title()}…"

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async for raw in proc.stdout:  # type: ignore[union-attr]
        line = _clean(raw.decode("utf-8", errors="replace"))
        if not line:
            continue
        for kw in ("EXTRACT", "TRANSFORM", "STAGING", "LOAD", "REFRESH", "VALIDATE"):
            if kw in line.upper():
                _job["message"] = line[-100:]
                break
        if progress_key == "stations_scraped" and line.startswith("Success"):
            m = re.search(r":\s*(\d+)", line)
            if m:
                _job["stations_scraped"] = int(m.group(1))
        if progress_key == "stations_loaded" and "Stations ins" in line:
            m = re.search(r":\s*([\d,]+)", line)
            if m:
                _job["stations_loaded"] = int(m.group(1).replace(",", ""))

    await proc.wait()
    return proc.returncode == 0


async def _run_pipeline() -> None:
    global _job

    python    = sys.executable
    triggered = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Snapshot BEFORE
    before = await _snapshot_stats()

    # ── Phase 1: scrape ───────────────────────────────────────────────────────
    ok = await _run_subprocess(
        [python, "-m", "scraper.pipeline.full_scrape"],
        phase_label="scraping",
        progress_key="stations_scraped",
    )
    if not ok:
        _job["phase"] = "error"
        _job["error"] = "Scraper exited with non-zero code. Check server logs."
        return

    # ── Phase 2: ETL ─────────────────────────────────────────────────────────
    ok = await _run_subprocess(
        [python, "-m", "etl.orchestrator"],
        phase_label="loading",
        progress_key="stations_loaded",
    )
    if not ok:
        _job["phase"] = "error"
        _job["error"] = "ETL exited with non-zero code. Check server logs."
        return

    # Snapshot AFTER
    after    = await _snapshot_stats()
    elapsed  = int(time.monotonic() - _start_mono) if _start_mono else 0
    delta    = {k: after.get(k, 0) - before.get(k, 0) for k in after}

    _append_run({
        "triggered_at":     triggered,
        "completed_at":     datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "duration_secs":    elapsed,
        "stations_scraped": _job["stations_scraped"],
        "stations_loaded":  _job["stations_loaded"],
        "before":           before,
        "after":            after,
        "delta":            delta,
    })

    _job["phase"]   = "done"
    _job["message"] = "Scrape complete — data is live."
