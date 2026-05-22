from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import orjson

from scraper.config import settings
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("pipeline.checkpoint")


@dataclass
class CheckpointState:
    run_id: str
    started_at: str
    last_updated: str
    total_stations: int
    completed_ids: set[int]
    failed_ids: dict[int, int]   # station_id -> retry_count
    last_completed_batch: int    # -1 means no batch completed yet
    batch_size: int
    concurrency: int


def _state_to_dict(state: CheckpointState) -> dict:
    return {
        "run_id": state.run_id,
        "started_at": state.started_at,
        "last_updated": state.last_updated,
        "total_stations": state.total_stations,
        "completed_ids": sorted(state.completed_ids),
        "failed_ids": {str(k): v for k, v in state.failed_ids.items()},
        "last_completed_batch": state.last_completed_batch,
        "batch_size": state.batch_size,
        "concurrency": state.concurrency,
    }


def _dict_to_state(d: dict) -> CheckpointState:
    return CheckpointState(
        run_id=d["run_id"],
        started_at=d["started_at"],
        last_updated=d["last_updated"],
        total_stations=d["total_stations"],
        completed_ids=set(d["completed_ids"]),
        failed_ids={int(k): v for k, v in d.get("failed_ids", {}).items()},
        last_completed_batch=d.get("last_completed_batch", -1),
        batch_size=d.get("batch_size", settings.scraper_batch_size),
        concurrency=d.get("concurrency", settings.scraper_concurrency),
    )


def find_latest_run(checkpoint_dir: Path) -> str | None:
    marker = checkpoint_dir / "latest_run_id.txt"
    if not marker.exists():
        return None
    run_id = marker.read_text(encoding="utf-8").strip()
    return run_id if run_id else None


class CheckpointManager:
    def __init__(self, checkpoint_dir: Path, run_id: str | None = None) -> None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._dir = checkpoint_dir
        self._run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._path = checkpoint_dir / f"run_{self._run_id}.json"

    @property
    def run_id(self) -> str:
        return self._run_id

    def load(self) -> CheckpointState:
        if self._path.exists():
            try:
                state = _dict_to_state(orjson.loads(self._path.read_bytes()))
                log.info(
                    "Loaded checkpoint: {n} completed, {f} failed",
                    n=len(state.completed_ids),
                    f=len(state.failed_ids),
                )
                return state
            except Exception as exc:
                log.warning("Checkpoint load failed ({e}), starting fresh", e=exc)
        state = CheckpointState(
            run_id=self._run_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
            total_stations=0,
            completed_ids=set(),
            failed_ids={},
            last_completed_batch=-1,
            batch_size=settings.scraper_batch_size,
            concurrency=settings.scraper_concurrency,
        )
        self.save(state)
        return state

    def save(self, state: CheckpointState) -> None:
        state.last_updated = datetime.now(timezone.utc).isoformat()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_bytes(orjson.dumps(_state_to_dict(state), option=orjson.OPT_INDENT_2))
        os.replace(tmp, self._path)
        (self._dir / "latest_run_id.txt").write_text(self._run_id, encoding="utf-8")

    def mark_completed(self, state: CheckpointState, station_id: int) -> None:
        state.completed_ids.add(station_id)
        state.failed_ids.pop(station_id, None)

    def mark_failed(self, state: CheckpointState, station_id: int) -> None:
        state.failed_ids[station_id] = state.failed_ids.get(station_id, 0) + 1

    def get_pending_ids(self, state: CheckpointState, all_ids: list[int]) -> list[int]:
        return sorted(sid for sid in all_ids if sid not in state.completed_ids)

    def get_retry_candidates(self, state: CheckpointState, max_retries: int) -> list[int]:
        return [sid for sid, count in state.failed_ids.items() if count < max_retries]
