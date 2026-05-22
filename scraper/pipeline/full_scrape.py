"""
Full-India scrape orchestrator.

Usage:
    python -m scraper.pipeline.full_scrape           # new run
    python -m scraper.pipeline.full_scrape --resume  # resume latest run
    python -m scraper.pipeline.full_scrape --run-id 20260521_130000
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import orjson
import pandas as pd

from scraper.config import settings
from scraper.pipeline.batch_runner import run_batches
from scraper.pipeline.checkpoint import CheckpointManager, find_latest_run
from scraper.pipeline.normalizer import NormalizedTables, normalize, save_normalized_tables
from scraper.pipeline.quality_metrics import QualityReport, compute_quality_report, save_quality_report
from scraper.models.station_detail import StationDetailResult
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("pipeline.full_scrape")


def _parse_args(argv: list[str]) -> tuple[bool, str | None]:
    """Returns (resume: bool, run_id: str | None)."""
    resume = "--resume" in argv
    run_id = None
    if "--run-id" in argv:
        idx = argv.index("--run-id")
        if idx + 1 < len(argv):
            run_id = argv[idx + 1]
    return resume, run_id


def _load_station_ids(csv_path: Path) -> list[int]:
    df = pd.read_csv(csv_path)
    return sorted(df["station_id"].astype(int).tolist())


def _load_all_results(details_dir: Path) -> list[StationDetailResult]:
    results: list[StationDetailResult] = []
    for json_path in sorted(details_dir.glob("*.json")):
        try:
            data = orjson.loads(json_path.read_bytes())
            results.append(StationDetailResult.model_validate(data))
        except Exception as exc:
            log.warning("Could not load result from {p}: {e}", p=json_path, e=exc)
    return results


def _format_elapsed(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins > 0:
        return f"{mins}m {secs:02d}s"
    return f"{secs}s"


async def run(argv: list[str]) -> None:
    resume, explicit_run_id = _parse_args(argv)

    if explicit_run_id:
        run_id = explicit_run_id
    elif resume:
        run_id = find_latest_run(settings.checkpoints_dir)
        if run_id is None:
            log.warning("--resume requested but no previous run found, starting fresh")
            run_id = None
    else:
        run_id = None  # CheckpointManager generates one

    checkpoint = CheckpointManager(settings.checkpoints_dir, run_id=run_id)
    state = checkpoint.load()

    csv_path = settings.exports_dir / "stations.csv"
    if not csv_path.exists():
        log.error(
            "stations.csv not found at {p} -- run station_list collector first",
            p=csv_path,
        )
        return

    all_ids = _load_station_ids(csv_path)
    if state.total_stations == 0:
        state.total_stations = len(all_ids)
        checkpoint.save(state)

    pending_ids = checkpoint.get_pending_ids(state, all_ids)
    retry_candidates = checkpoint.get_retry_candidates(state, settings.scraper_max_retries)
    for sid in retry_candidates:
        if sid not in pending_ids:
            pending_ids.append(sid)
    pending_ids = sorted(set(pending_ids))

    log.info(
        "Run {run_id} | total={total} | completed={done} | pending={pend} | failed={fail}",
        run_id=checkpoint.run_id,
        total=len(all_ids),
        done=len(state.completed_ids),
        pend=len(pending_ids),
        fail=len(state.failed_ids),
    )

    if not pending_ids:
        log.info("Already complete -- nothing to scrape")
        print("Already complete -- nothing to scrape.")
        return

    t0 = time.monotonic()
    await run_batches(
        pending_ids,
        checkpoint,
        batch_size=settings.scraper_batch_size,
        concurrency=settings.scraper_concurrency,
        jitter_min=settings.scraper_batch_jitter_min,
        jitter_max=settings.scraper_batch_jitter_max,
    )
    elapsed = time.monotonic() - t0

    # Load ALL results for quality metrics (including prior runs)
    details_dir = settings.processed_data_dir / "details"
    all_results = _load_all_results(details_dir)
    log.info("Loaded {n} total processed results for quality report", n=len(all_results))

    report = compute_quality_report(all_results, checkpoint.run_id, elapsed)
    report_path = save_quality_report(report, settings.reports_dir)

    tables = normalize(all_results)
    save_normalized_tables(tables, settings.final_data_dir, all_results)

    failed_state = checkpoint.load()
    failed_path = settings.failed_data_dir / "failed_station_ids.json"
    failed_path.write_bytes(
        orjson.dumps(
            {
                "run_id": checkpoint.run_id,
                "failed_ids": {str(k): v for k, v in failed_state.failed_ids.items()},
            },
            option=orjson.OPT_INDENT_2,
        )
    )

    print()
    print("=" * 50)
    print("FULL SCRAPE COMPLETE")
    print("=" * 50)
    print(f"Run ID       : {checkpoint.run_id}")
    print(f"Total        : {report.total_attempted} stations")
    print(f"Success      : {report.parse_success} ({report.success_rate_pct:.1f}%)")
    print(f"Failed       : {report.parse_failed}")
    print(f"Elapsed      : {_format_elapsed(elapsed)}")
    print(f"Avg coverage : {report.avg_coverage_pct:.1f}%")
    print(f"Report       : {report_path}")
    print(f"Final data   : {settings.final_data_dir}")
    print("=" * 50)


def main() -> None:
    asyncio.run(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
