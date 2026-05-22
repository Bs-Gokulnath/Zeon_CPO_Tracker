from __future__ import annotations

import asyncio
import gzip
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import orjson
import pandas as pd

from scraper.config import settings
from scraper.http.client import AsyncHTTPClient
from scraper.models.station_detail import StationDetailResult
from scraper.parsers.rsc_parser import extract_station_detail_result
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("collectors.station_detail")

_RSC_HEADERS = {"RSC": "1", "Accept": "text/x-component"}

# Captive/private station IDs selected for coverage testing
_PRIVATE_IDS = [8312, 14633]
# Unavailable public AC station
_UNAVAILABLE_AC_ID = 1155
# Station with zero reviews
_ZERO_REVIEWS_ID = 15886
# High-traffic station
_HIGH_TRAFFIC_ID = 1158


async def scrape_station_detail(
    station_id: int,
    session: AsyncHTTPClient,
    semaphore: asyncio.Semaphore,
) -> StationDetailResult:
    """Fetch and parse one station's detail page."""
    scraped_at = datetime.now(timezone.utc).isoformat()

    async with semaphore:
        url = f"{settings.statiq_base_url}/x-ev-charging-station-id-{station_id}?__flight__=1"

        try:
            response = await session.get(url, extra_headers=_RSC_HEADERS)
        except Exception as exc:
            log.error(
                "HTTP fetch failed for station {sid}: {e}",
                sid=station_id,
                e=exc,
            )
            return StationDetailResult(
                station_id=station_id,
                scraped_at=scraped_at,
                parse_success=False,
            )

        if settings.store_raw_rsc:
            raw_dir = settings.raw_data_dir / "details"
            raw_dir.mkdir(parents=True, exist_ok=True)
            if settings.compress_raw_rsc:
                raw_path = raw_dir / f"station_{station_id}.txt.gz"
                raw_path.write_bytes(gzip.compress(response.text.encode("utf-8")))
            else:
                raw_path = raw_dir / f"station_{station_id}.txt"
                raw_path.write_text(response.text, encoding="utf-8")
            log.debug(
                "Saved raw RSC payload -> {path} ({size} bytes)",
                path=raw_path,
                size=len(response.content),
            )

        result = extract_station_detail_result(response.text, station_id)

        processed_dir = settings.processed_data_dir / "details"
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed_path = processed_dir / f"station_{station_id}.json"
        processed_path.write_bytes(
            orjson.dumps(
                result.model_dump(),
                option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
            )
        )
        log.info(
            "Scraped station {sid} — parse_success={ok} coverage={cov:.1f}%",
            sid=station_id,
            ok=result.parse_success,
            cov=result.coverage_pct,
        )

        return result


async def scrape_station_details_batch(
    station_ids: list[int],
    *,
    concurrency: int = 10,
) -> list[StationDetailResult]:
    """Scrape a batch of stations concurrently."""
    semaphore = asyncio.Semaphore(concurrency)
    async with AsyncHTTPClient(read_timeout=settings.scraper_request_timeout) as session:
        tasks = [
            scrape_station_detail(sid, session, semaphore)
            for sid in station_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


def _select_sample_ids() -> list[int]:
    """
    Build the 10-station sample:
      - 2 private/captive
      - 1 unavailable AC
      - 1 zero-reviews
      - 1 high-traffic
      - 5 random public stations (seed=42)
    """
    fixed_ids = {
        *_PRIVATE_IDS,
        _UNAVAILABLE_AC_ID,
        _ZERO_REVIEWS_ID,
        _HIGH_TRAFFIC_ID,
    }

    csv_path = settings.exports_dir / "stations.csv"
    if not csv_path.exists():
        log.warning("stations.csv not found at {p} — using fixed IDs only", p=csv_path)
        return sorted(fixed_ids)

    df = pd.read_csv(csv_path)
    public_df = df[
        (df["access_type"] == 1)
        & (~df["station_id"].isin(fixed_ids))
    ]

    rng = random.Random(42)
    random_ids = rng.sample(list(public_df["station_id"].astype(int)), min(5, len(public_df)))

    all_ids = sorted(fixed_ids | set(random_ids))
    log.info(
        "Sample station IDs ({n} total): {ids}",
        n=len(all_ids),
        ids=all_ids,
    )
    return all_ids


async def run_sample() -> None:
    t0 = time.monotonic()

    station_ids = _select_sample_ids()
    results = await scrape_station_details_batch(station_ids, concurrency=5)

    elapsed = time.monotonic() - t0

    # -- Validation report -----------------------------------------------------
    print("\n" + "=" * 80)
    print("STATION DETAIL SCRAPE -- VALIDATION REPORT")
    print("=" * 80)

    header = f"{'ID':>8}  {'Name':<40}  {'OK':>4}  {'Cov%':>6}  {'Chgrs':>5}  {'Cons':>5}  Missing"
    print(header)
    print("-" * 80)

    success_count = 0
    total_coverage = 0.0

    for r in results:
        if r.parse_success:
            success_count += 1
            total_coverage += r.coverage_pct

        name = ""
        charger_count = 0
        connector_count = 0

        if r.station_detail:
            name = (r.station_detail.station_name or "")[:40]
            charger_count = len(r.station_detail.plugin_details)
            connector_count = sum(
                len(p.connectors) for p in r.station_detail.plugin_details
            )

        missing_summary = ", ".join(r.missing_fields[:5])
        if len(r.missing_fields) > 5:
            missing_summary += f" (+{len(r.missing_fields) - 5} more)"

        print(
            f"{r.station_id:>8}  {name:<40}  {'Y' if r.parse_success else 'N':>4}  "
            f"{r.coverage_pct:>6.1f}  {charger_count:>5}  {connector_count:>5}  "
            f"{missing_summary}"
        )

    print("-" * 80)

    total = len(results)
    avg_cov = total_coverage / success_count if success_count else 0.0

    print(f"\nSuccess rate  : {success_count}/{total} ({success_count / total * 100:.0f}%)")
    print(f"Avg coverage  : {avg_cov:.1f}%")
    print(f"Total elapsed : {elapsed:.1f}s")
    print("=" * 80)


def main() -> None:
    asyncio.run(run_sample())


if __name__ == "__main__":
    main()
