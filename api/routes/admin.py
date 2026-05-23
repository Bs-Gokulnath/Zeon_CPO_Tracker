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


# ── Detailed diff ─────────────────────────────────────────────────────────────

@router.get("/scrape/runs")
async def list_runs(limit: int = 50) -> list[dict]:
    """Past scrape runs, newest first, with per-run station counts."""
    async with AsyncSession(engine) as session:
        rows = await session.execute(text("""
            SELECT
                r.run_id,
                r.started_at,
                r.completed_at,
                COALESCE(
                    EXTRACT(EPOCH FROM (r.completed_at - r.started_at))::int,
                    0
                )                                                          AS duration_secs,
                (SELECT COUNT(DISTINCT station_id) FROM station_status_history
                    WHERE scrape_run_id = r.run_id)                        AS stations_in_run,
                (SELECT COUNT(DISTINCT station_id) FROM station_status_history
                    WHERE scrape_run_id = r.run_id
                      AND availability = 'Available')                      AS available_in_run
            FROM scrape_runs r
            ORDER BY r.started_at DESC
            LIMIT :limit
        """), {"limit": limit})
        return [dict(r._mapping) for r in rows.all()]


@router.get("/scrape/runs/{run_id}/diff")
async def run_diff(run_id: str, sample: int = 200) -> dict:
    """
    Compute the difference between *run_id* and the immediately preceding run.

    Returns:
      - meta: this & previous run_id + timestamps
      - summary: aggregate counts (added / removed / changed / unchanged)
      - added:   newly-scraped stations (full station meta)
      - removed: stations that disappeared (full station meta)
      - changed: stations whose tracked status fields differ — with old → new
                 for availability / avg_rating / review_count / available_connector_count

    `sample` caps the size of each list returned (default 200 — UI shows
    paginated table).
    """
    async with AsyncSession(engine) as session:
        # Find previous run
        prev_row = await session.execute(text("""
            SELECT run_id, started_at, completed_at
            FROM scrape_runs
            WHERE started_at < (SELECT started_at FROM scrape_runs WHERE run_id = :rid)
            ORDER BY started_at DESC
            LIMIT 1
        """), {"rid": run_id})
        prev = prev_row.first()

        cur_row = await session.execute(text("""
            SELECT run_id, started_at, completed_at FROM scrape_runs WHERE run_id = :rid
        """), {"rid": run_id})
        cur = cur_row.first()
        if not cur:
            return {"error": f"run_id {run_id} not found"}

        meta = {
            "this_run":     {"run_id": cur.run_id, "started_at": cur.started_at.isoformat() if cur.started_at else None,
                             "completed_at": cur.completed_at.isoformat() if cur.completed_at else None},
            "previous_run": None if not prev else {
                "run_id": prev.run_id,
                "started_at": prev.started_at.isoformat() if prev.started_at else None,
                "completed_at": prev.completed_at.isoformat() if prev.completed_at else None,
            },
        }

        # Counts in each run
        cur_count = (await session.execute(text(
            "SELECT COUNT(DISTINCT station_id) FROM station_status_history WHERE scrape_run_id = :rid"
        ), {"rid": run_id})).scalar() or 0

        if not prev:
            # First-ever run — nothing to compare against
            return {
                **meta,
                "summary": {"added": cur_count, "removed": 0, "changed": 0,
                            "unchanged": 0, "before_total": 0, "after_total": cur_count},
                "added": [], "removed": [], "changed": [],
                "note": "No previous run to diff against — this is the first scrape.",
            }

        prev_count = (await session.execute(text(
            "SELECT COUNT(DISTINCT station_id) FROM station_status_history WHERE scrape_run_id = :rid"
        ), {"rid": prev.run_id})).scalar() or 0

        # Added stations
        added_rows = await session.execute(text("""
            SELECT s.id, s.station_name, s.city_name_cached AS city_name,
                   st.name AS state_name, s.operator_name_cached AS operator_name,
                   s.charger_type, t.availability, t.avg_rating, t.review_count,
                   t.available_connector_count
            FROM station_status_history t
            JOIN stations s ON s.id = t.station_id
            LEFT JOIN states st ON st.id = s.state_id
            WHERE t.scrape_run_id = :rid
              AND t.station_id NOT IN (
                  SELECT station_id FROM station_status_history WHERE scrape_run_id = :prid
              )
            ORDER BY s.station_name
            LIMIT :lim
        """), {"rid": run_id, "prid": prev.run_id, "lim": sample})
        added = [dict(r._mapping) for r in added_rows.all()]

        # Total added (for accurate summary even when list is capped)
        added_total = (await session.execute(text("""
            SELECT COUNT(*) FROM station_status_history
            WHERE scrape_run_id = :rid
              AND station_id NOT IN (
                  SELECT station_id FROM station_status_history WHERE scrape_run_id = :prid
              )
        """), {"rid": run_id, "prid": prev.run_id})).scalar() or 0

        # Removed stations
        removed_rows = await session.execute(text("""
            SELECT s.id, s.station_name, s.city_name_cached AS city_name,
                   st.name AS state_name, s.operator_name_cached AS operator_name,
                   s.charger_type, p.availability AS last_availability,
                   p.avg_rating AS last_rating
            FROM station_status_history p
            JOIN stations s ON s.id = p.station_id
            LEFT JOIN states st ON st.id = s.state_id
            WHERE p.scrape_run_id = :prid
              AND p.station_id NOT IN (
                  SELECT station_id FROM station_status_history WHERE scrape_run_id = :rid
              )
            ORDER BY s.station_name
            LIMIT :lim
        """), {"prid": prev.run_id, "rid": run_id, "lim": sample})
        removed = [dict(r._mapping) for r in removed_rows.all()]

        removed_total = (await session.execute(text("""
            SELECT COUNT(*) FROM station_status_history
            WHERE scrape_run_id = :prid
              AND station_id NOT IN (
                  SELECT station_id FROM station_status_history WHERE scrape_run_id = :rid
              )
        """), {"prid": prev.run_id, "rid": run_id})).scalar() or 0

        # Changed stations — same station in both runs, at least one tracked field differs
        changed_rows = await session.execute(text("""
            SELECT s.id, s.station_name, s.city_name_cached AS city_name,
                   st.name AS state_name, s.operator_name_cached AS operator_name,
                   p.availability                AS old_availability,
                   t.availability                AS new_availability,
                   p.avg_rating                  AS old_avg_rating,
                   t.avg_rating                  AS new_avg_rating,
                   p.review_count                AS old_review_count,
                   t.review_count                AS new_review_count,
                   p.available_connector_count   AS old_available_connectors,
                   t.available_connector_count   AS new_available_connectors
            FROM station_status_history t
            JOIN station_status_history p
              ON p.station_id = t.station_id AND p.scrape_run_id = :prid
            JOIN stations s ON s.id = t.station_id
            LEFT JOIN states st ON st.id = s.state_id
            WHERE t.scrape_run_id = :rid
              AND (
                   p.availability                IS DISTINCT FROM t.availability
                OR p.avg_rating                  IS DISTINCT FROM t.avg_rating
                OR p.review_count                IS DISTINCT FROM t.review_count
                OR p.available_connector_count   IS DISTINCT FROM t.available_connector_count
              )
            ORDER BY
              (p.availability IS DISTINCT FROM t.availability) DESC,
              s.station_name
            LIMIT :lim
        """), {"prid": prev.run_id, "rid": run_id, "lim": sample})
        changed = [dict(r._mapping) for r in changed_rows.all()]

        changed_total = (await session.execute(text("""
            SELECT COUNT(*) FROM station_status_history t
            JOIN station_status_history p
              ON p.station_id = t.station_id AND p.scrape_run_id = :prid
            WHERE t.scrape_run_id = :rid
              AND (
                   p.availability                IS DISTINCT FROM t.availability
                OR p.avg_rating                  IS DISTINCT FROM t.avg_rating
                OR p.review_count                IS DISTINCT FROM t.review_count
                OR p.available_connector_count   IS DISTINCT FROM t.available_connector_count
              )
        """), {"prid": prev.run_id, "rid": run_id})).scalar() or 0

        unchanged = max(0, prev_count - removed_total - changed_total)

        return {
            **meta,
            "summary": {
                "before_total":  prev_count,
                "after_total":   cur_count,
                "added":         added_total,
                "removed":       removed_total,
                "changed":       changed_total,
                "unchanged":     unchanged,
                "list_capped_at": sample,
            },
            "added":   added,
            "removed": removed,
            "changed": changed,
        }


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
