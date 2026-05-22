from __future__ import annotations

"""
API Benchmark — Step 6 validation.

Fires requests against the running API and reports p50/p95 latencies.

Usage:
    python -m api.benchmark
    python -m api.benchmark --base-url http://localhost:8000 --runs 20
"""

import asyncio
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import orjson

_DEFAULT_BASE = "http://localhost:8000"
_DEFAULT_RUNS = 20


@dataclass
class EndpointResult:
    name:        str
    url:         str
    target_ms:   float
    samples:     list[float] = field(default_factory=list)
    errors:      int = 0
    status_codes: list[int] = field(default_factory=list)

    @property
    def p50(self) -> float:
        return statistics.median(self.samples) if self.samples else 0

    @property
    def p95(self) -> float:
        if not self.samples:
            return 0
        k = max(1, int(len(self.samples) * 0.95))
        return sorted(self.samples)[k - 1]

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0

    @property
    def passed(self) -> bool:
        return self.p95 <= self.target_ms


async def _measure(
    client: httpx.AsyncClient,
    result: EndpointResult,
    runs: int,
) -> None:
    # Warm-up run (excluded from stats)
    try:
        await client.get(result.url)
    except Exception:
        pass

    for _ in range(runs):
        t0 = time.perf_counter()
        try:
            resp = await client.get(result.url)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            result.samples.append(elapsed_ms)
            result.status_codes.append(resp.status_code)
        except Exception as exc:
            result.errors += 1


async def run_benchmark(base_url: str, runs: int, reports_dir: Path) -> None:
    endpoints = [
        ("GET /health",                    f"{base_url}/health",                               200),
        ("GET /stations (no filter)",       f"{base_url}/stations?page_size=50",               150),
        ("GET /stations (state filter)",    f"{base_url}/stations?state_id=1&page_size=50",    150),
        ("GET /stations (city+type+avail)", f"{base_url}/stations?city_id=1&charger_type=DC&availability=Available", 150),
        ("GET /stations (text search)",     f"{base_url}/stations?q=chennai&page_size=20",     150),
        ("GET /stations/{id} (detail)",     f"{base_url}/stations/1",                          200),
        ("GET /filters",                    f"{base_url}/filters",                             100),
        ("GET /search?q=chennai",           f"{base_url}/search?q=chennai",                    50),
        ("GET /search/autocomplete?q=stat", f"{base_url}/search/autocomplete?q=stat",          50),
        ("GET /analytics/overview",         f"{base_url}/analytics/overview",                 100),
        ("GET /analytics/state-dist",       f"{base_url}/analytics/state-distribution",       100),
        ("GET /analytics/operator-dist",    f"{base_url}/analytics/operator-distribution",    100),
        ("GET /analytics/charger-speed",    f"{base_url}/analytics/charger-speed",            100),
        ("GET /analytics/ac-dc",            f"{base_url}/analytics/ac-dc-breakdown",          100),
        ("GET /nearby (Haversine 5km)",     f"{base_url}/nearby?lat=28.6&lon=77.2&radius_km=5", 250),
    ]

    results = [EndpointResult(name=n, url=u, target_ms=t) for n, u, t in endpoints]

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Run all endpoint benchmarks concurrently
        await asyncio.gather(*[_measure(client, r, runs) for r in results])

    _print_report(results, runs)
    _save_report(results, runs, reports_dir)


def _print_report(results: list[EndpointResult], runs: int) -> None:
    print()
    print("=" * 80)
    print(f"API BENCHMARK REPORT  ({runs} samples per endpoint)")
    print("=" * 80)
    print(f"{'Endpoint':<42} {'p50':>7} {'p95':>7} {'mean':>7} {'target':>8}  {'status'}")
    print("-" * 80)
    for r in results:
        status = "PASS" if r.passed else "FAIL <--"
        errors = f" ({r.errors} err)" if r.errors else ""
        print(
            f"{r.name:<42} {r.p50:>6.1f}ms {r.p95:>6.1f}ms {r.mean:>6.1f}ms"
            f" {r.target_ms:>7.0f}ms  {status}{errors}"
        )
    print()
    passed = sum(r.passed for r in results)
    print(f"Overall: {passed}/{len(results)} endpoints within p95 target")

    slow = [r for r in results if not r.passed]
    if slow:
        print("\nSlow endpoints:")
        for r in slow:
            print(f"  {r.name}: p95={r.p95:.1f}ms (target {r.target_ms:.0f}ms)")
    print("=" * 80)


def _save_report(results: list[EndpointResult], runs: int, reports_dir: Path) -> None:
    data = {
        "runs_per_endpoint": runs,
        "endpoints": [
            {
                "name":       r.name,
                "url":        r.url,
                "target_ms":  r.target_ms,
                "p50_ms":     round(r.p50, 2),
                "p95_ms":     round(r.p95, 2),
                "mean_ms":    round(r.mean, 2),
                "errors":     r.errors,
                "passed":     r.passed,
            }
            for r in results
        ],
        "overall_passed": all(r.passed for r in results),
        "passed_count":   sum(r.passed for r in results),
        "total_count":    len(results),
    }
    path = reports_dir / "api_benchmark_report.json"
    path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    print(f"\nReport saved → {path}")


def _parse_args(argv: list[str]) -> tuple[str, int]:
    base_url = _DEFAULT_BASE
    runs     = _DEFAULT_RUNS
    if "--base-url" in argv:
        i = argv.index("--base-url")
        if i + 1 < len(argv):
            base_url = argv[i + 1]
    if "--runs" in argv:
        i = argv.index("--runs")
        if i + 1 < len(argv):
            runs = int(argv[i + 1])
    return base_url, runs


def main() -> None:
    from scraper.config import settings
    base_url, runs = _parse_args(sys.argv[1:])
    asyncio.run(run_benchmark(base_url, runs, settings.reports_dir))


if __name__ == "__main__":
    main()
