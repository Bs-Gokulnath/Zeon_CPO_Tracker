"""
Admin route — scrape trigger and status.
POST /admin/scrape/trigger  → launches full_scrape + etl.orchestrator as subprocesses
GET  /admin/scrape/status   → returns current job state (polled by the frontend)
"""
from __future__ import annotations

import asyncio
import re
import sys
import time
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

_job: dict[str, Any] = {
    "phase":    "idle",   # idle | scraping | loading | done | error
    "message":  "",
    "started_at": None,
    "elapsed_secs": 0,
    "stations_scraped": 0,
    "stations_loaded":  0,
    "error":    None,
}
_start_mono: float | None = None


def _clean(line: str) -> str:
    return _ANSI.sub("", line).strip()


@router.get("/scrape/status")
async def scrape_status() -> dict:
    result = dict(_job)
    result["elapsed_secs"] = int(time.monotonic() - _start_mono) if _start_mono else 0
    return result


@router.post("/scrape/trigger")
async def scrape_trigger() -> dict:
    global _job, _start_mono

    if _job["phase"] in ("scraping", "loading"):
        return {"ok": False, "message": f"Already running: {_job['phase']}"}

    _start_mono = time.monotonic()
    _job = {
        "phase":    "scraping",
        "message":  "Starting scrape…",
        "started_at": None,
        "elapsed_secs": 0,
        "stations_scraped": 0,
        "stations_loaded":  0,
        "error":    None,
    }

    asyncio.create_task(_run_pipeline())
    return {"ok": True}


async def _run_subprocess(args: list[str], phase_label: str, progress_key: str) -> bool:
    """Run a subprocess, stream stdout, parse progress. Returns True on success."""
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

        # Pick up log-level keywords for the message label
        for kw in ("EXTRACT", "TRANSFORM", "STAGING", "LOAD", "REFRESH", "VALIDATE"):
            if kw in line.upper():
                _job["message"] = line[-100:]
                break

        # Parse scrape summary: "Success      : 1234 (95.0%)"
        if progress_key == "stations_scraped" and line.startswith("Success"):
            m = re.search(r":\s*(\d+)", line)
            if m:
                _job["stations_scraped"] = int(m.group(1))

        # Parse ETL summary: "Stations ins : 1234"
        if progress_key == "stations_loaded" and "Stations ins" in line:
            m = re.search(r":\s*([\d,]+)", line)
            if m:
                _job["stations_loaded"] = int(m.group(1).replace(",", ""))

    await proc.wait()
    return proc.returncode == 0


async def _run_pipeline() -> None:
    global _job

    python = sys.executable

    # ── Phase 1: full scrape ──────────────────────────────────────────────────
    ok = await _run_subprocess(
        [python, "-m", "scraper.pipeline.full_scrape"],
        phase_label="scraping",
        progress_key="stations_scraped",
    )
    if not ok:
        _job["phase"] = "error"
        _job["error"] = "Scraper exited with non-zero code. Check server logs."
        return

    # ── Phase 2: ETL ──────────────────────────────────────────────────────────
    ok = await _run_subprocess(
        [python, "-m", "etl.orchestrator"],
        phase_label="loading",
        progress_key="stations_loaded",
    )
    if not ok:
        _job["phase"] = "error"
        _job["error"] = "ETL exited with non-zero code. Check server logs."
        return

    _job["phase"]   = "done"
    _job["message"] = "Scrape complete — data is live."
