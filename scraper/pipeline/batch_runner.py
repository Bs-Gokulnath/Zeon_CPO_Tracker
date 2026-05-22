from __future__ import annotations

import asyncio
import random
import time

from scraper.collectors.station_detail import scrape_station_details_batch
from scraper.config import settings
from scraper.models.station_detail import StationDetailResult
from scraper.pipeline.checkpoint import CheckpointManager, CheckpointState
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("pipeline.batch_runner")


def _split_batches(ids: list[int], size: int) -> list[list[int]]:
    return [ids[i : i + size] for i in range(0, len(ids), size)]


def _format_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs:02d}s"


async def run_batches(
    all_pending_ids: list[int],
    checkpoint: CheckpointManager,
    *,
    batch_size: int | None = None,
    concurrency: int | None = None,
    jitter_min: float | None = None,
    jitter_max: float | None = None,
) -> list[StationDetailResult]:
    batch_size = batch_size or settings.scraper_batch_size
    concurrency = concurrency or settings.scraper_concurrency
    jitter_min = jitter_min if jitter_min is not None else settings.scraper_batch_jitter_min
    jitter_max = jitter_max if jitter_max is not None else settings.scraper_batch_jitter_max

    state: CheckpointState = checkpoint.load()
    batches = _split_batches(all_pending_ids, batch_size)
    total_batches = len(batches)
    total_stations = len(all_pending_ids)

    log.info(
        "Starting {n} batches of {bs} (concurrency={c}, total={t} stations)",
        n=total_batches,
        bs=batch_size,
        c=concurrency,
        t=total_stations,
    )

    all_results: list[StationDetailResult] = []
    batch_times: list[float] = []
    total_success = 0
    total_failed = 0

    for i, batch_ids in enumerate(batches):
        batch_start = state.last_completed_batch + 1
        if i < batch_start:
            log.debug("Skipping already-completed batch {i}", i=i)
            continue

        batch_t0 = time.monotonic()
        log.info(
            "Batch {cur}/{total} -- {n} stations (total completed so far: {done}/{all})",
            cur=i + 1,
            total=total_batches,
            n=len(batch_ids),
            done=len(state.completed_ids),
            all=total_stations,
        )

        results = await scrape_station_details_batch(batch_ids, concurrency=concurrency)
        all_results.extend(results)

        batch_success = 0
        batch_failed = 0
        for r in results:
            if r.parse_success:
                checkpoint.mark_completed(state, r.station_id)
                batch_success += 1
                total_success += 1
            else:
                checkpoint.mark_failed(state, r.station_id)
                batch_failed += 1
                total_failed += 1

        state.last_completed_batch = i
        checkpoint.save(state)

        batch_elapsed = time.monotonic() - batch_t0
        batch_times.append(batch_elapsed)
        avg_batch = sum(batch_times) / len(batch_times)
        remaining = total_batches - (i + 1)
        eta_str = _format_eta(remaining * avg_batch)

        log.info(
            "Batch {cur}/{total} done -- success={ok} failed={fail} | "
            "total_completed={done}/{all} | ETA {eta}",
            cur=i + 1,
            total=total_batches,
            ok=batch_success,
            fail=batch_failed,
            done=len(state.completed_ids),
            all=total_stations,
            eta=eta_str,
        )

        if i < total_batches - 1:
            sleep_secs = random.uniform(jitter_min, jitter_max)
            log.debug("Sleeping {s:.1f}s before next batch", s=sleep_secs)
            await asyncio.sleep(sleep_secs)

    log.info(
        "All batches complete -- success={ok} failed={fail}",
        ok=total_success,
        fail=total_failed,
    )
    return all_results
