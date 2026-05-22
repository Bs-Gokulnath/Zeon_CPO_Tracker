from __future__ import annotations

"""
ETL Benchmark — Step 5C performance validation.

Runs EXPLAIN ANALYZE on key dashboard queries and emits a structured report.

Usage:
    python -m etl.benchmark
    python -m etl.benchmark --run-id 20260521_075852
"""

import asyncio
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import asyncpg
import orjson

from scraper.config import settings
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.benchmark")

_TARGET_MS = {
    "state_filter":         50.0,
    "city_charger_filter":  100.0,
    "fulltext_janak":       50.0,
    "fulltext_itc":         50.0,
    "fulltext_petrol":      50.0,
    "fulltext_chennai":     50.0,
    "mv_operator":          20.0,
    "mv_state":             20.0,
    "mv_city":              20.0,
    "mv_charger_speed":     20.0,
    "mv_ac_dc":             20.0,
}


@dataclass
class QueryResult:
    name: str
    sql_preview: str
    target_ms: float
    execution_ms: float = 0.0
    planning_ms: float = 0.0
    rows_returned: int = 0
    plan_type: str = ""   # "Index Scan", "Seq Scan", "Bitmap Heap Scan", ...
    passed: bool = False
    plan_text: str = ""


@dataclass
class BenchmarkReport:
    run_id: str
    timestamp: str
    elapsed_secs: float = 0.0
    queries: list[QueryResult] = field(default_factory=list)
    overall_passed: bool = True
    index_stats: list[dict] = field(default_factory=list)
    db_version: str = ""
    postgis_available: bool = False
    city_state_nulls: int = 0
    total_stations: int = 0


def _parse_plan(rows: list) -> tuple[float, float, int, str]:
    """Extract execution_ms, planning_ms, rows, plan_type from EXPLAIN ANALYZE output."""
    text = "\n".join(r[0] for r in rows)
    exec_match = re.search(r"Execution Time:\s+([\d.]+)\s+ms", text)
    plan_match  = re.search(r"Planning Time:\s+([\d.]+)\s+ms", text)
    rows_match  = re.search(r"rows=(\d+)", text)

    exec_ms  = float(exec_match.group(1))  if exec_match  else 0.0
    plan_ms  = float(plan_match.group(1))  if plan_match  else 0.0
    rows_out = int(rows_match.group(1))    if rows_match  else 0

    # Identify dominant scan type — order matters: Bitmap before bare "Index Scan"
    # to avoid "Index Scan" matching as substring of "Bitmap Index Scan"
    type_map = [
        ("Bitmap Heap Scan",  "Bitmap Heap Scan (GIN/GiST)"),
        ("Index Only Scan",   "Index Only Scan"),
        ("Index Scan",        "Index Scan"),
        ("Seq Scan",          "Seq Scan"),
    ]
    plan_type = "Unknown"
    for marker, label in type_map:
        if marker in text:
            plan_type = label
            break

    return exec_ms, plan_ms, rows_out, plan_type


async def _run_query(
    conn: asyncpg.Connection,
    name: str,
    sql: str,
    target_ms: float,
    warmup_sql: str | None = None,
) -> QueryResult:
    # Warm up plan cache (run once without EXPLAIN)
    if warmup_sql:
        try:
            await conn.execute(warmup_sql)
        except Exception:
            pass

    plan_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}"
    rows = await conn.fetch(plan_sql)
    exec_ms, plan_ms, n_rows, plan_type = _parse_plan(rows)
    plan_text = "\n".join(r[0] for r in rows)

    result = QueryResult(
        name=name,
        sql_preview=sql[:120].replace("\n", " ").strip(),
        target_ms=target_ms,
        execution_ms=round(exec_ms, 3),
        planning_ms=round(plan_ms, 3),
        rows_returned=n_rows,
        plan_type=plan_type,
        passed=exec_ms <= target_ms,
        plan_text=plan_text,
    )
    status = "PASS" if result.passed else "FAIL"
    log.info(
        "{status} {name}: {ms:.1f}ms (target {t}ms) — {pt}",
        status=status, name=name, ms=exec_ms, t=target_ms, pt=plan_type,
    )
    return result


async def _get_sample_ids(conn: asyncpg.Connection) -> dict:
    """Fetch representative IDs for parameterised queries."""
    state_row = await conn.fetchrow(
        "SELECT id FROM states ORDER BY id LIMIT 1"
    )
    city_row = await conn.fetchrow(
        """SELECT city_id FROM stations
           WHERE city_id IS NOT NULL AND charger_type = 'DC'
             AND availability = 'Available'
           LIMIT 1"""
    )
    return {
        "state_id": state_row["id"] if state_row else 1,
        "city_id":  city_row["city_id"] if city_row else 1,
    }


async def run_benchmark(run_id: str, reports_dir: Path) -> BenchmarkReport:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    t0 = time.monotonic()

    report = BenchmarkReport(
        run_id=run_id,
        timestamp=__import__("datetime").datetime.utcnow().isoformat(),
    )

    async with pool.acquire() as conn:
        report.db_version = (await conn.fetchval("SELECT version()"))[:60]
        report.postgis_available = bool(
            await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname='postgis'")
        )
        report.total_stations = await conn.fetchval("SELECT COUNT(*) FROM stations")
        report.city_state_nulls = await conn.fetchval(
            "SELECT COUNT(*) FROM stations WHERE city_id IS NULL"
        )

        ids = await _get_sample_ids(conn)
        state_id = ids["state_id"]
        city_id  = ids["city_id"]

        # ── A: State filter ───────────────────────────────────────────────────
        report.queries.append(await _run_query(
            conn, "state_filter",
            f"""SELECT id, station_name, city_id, availability, avg_rating
                FROM stations WHERE state_id = {state_id} LIMIT 200""",
            target_ms=_TARGET_MS["state_filter"],
        ))

        # ── B: City + charger_type + availability filter ───────────────────────
        report.queries.append(await _run_query(
            conn, "city_charger_filter",
            f"""SELECT id, station_name, avg_rating, availability
                FROM stations
                WHERE city_id = {city_id}
                  AND charger_type = 'DC'
                  AND availability = 'Available'
                ORDER BY avg_rating DESC NULLS LAST
                LIMIT 50""",
            target_ms=_TARGET_MS["city_charger_filter"],
        ))

        # ── D: Full-text search ───────────────────────────────────────────────
        for term in ("janak", "itc", "petrol", "chennai"):
            report.queries.append(await _run_query(
                conn, f"fulltext_{term}",
                f"""SELECT id, station_name, city_name_cached
                    FROM stations
                    WHERE search_vector @@ to_tsquery('simple', '{term}')
                    LIMIT 20""",
                target_ms=_TARGET_MS[f"fulltext_{term}"],
            ))

        # ── E: Materialized view queries ──────────────────────────────────────
        mv_queries = [
            ("mv_operator",     "SELECT * FROM mv_operator_distribution"),
            ("mv_state",        "SELECT * FROM mv_state_station_distribution"),
            ("mv_city",         "SELECT * FROM mv_city_station_distribution LIMIT 100"),
            ("mv_charger_speed","SELECT * FROM mv_charger_speed_distribution"),
            ("mv_ac_dc",        "SELECT * FROM mv_ac_dc_breakdown"),
        ]
        for name, sql in mv_queries:
            report.queries.append(await _run_query(
                conn, name, sql, target_ms=_TARGET_MS[name]
            ))

        # ── Index usage stats ─────────────────────────────────────────────────
        idx_rows = await conn.fetch("""
            SELECT
                indexrelname                                       AS index_name,
                relname                                            AS table_name,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid))       AS index_size
            FROM pg_stat_user_indexes
            ORDER BY relname, idx_scan ASC
        """)
        report.index_stats = [dict(r) for r in idx_rows]

    await pool.close()
    report.elapsed_secs = round(time.monotonic() - t0, 3)
    report.overall_passed = all(q.passed for q in report.queries)

    # Save report (omit verbose plan_text from JSON to keep it readable)
    def _serialise(q: QueryResult) -> dict:
        d = asdict(q)
        del d["plan_text"]
        return d

    out = {
        "run_id":           report.run_id,
        "timestamp":        report.timestamp,
        "elapsed_secs":     report.elapsed_secs,
        "db_version":       report.db_version,
        "postgis_available":report.postgis_available,
        "total_stations":   report.total_stations,
        "city_state_nulls": report.city_state_nulls,
        "overall_passed":   report.overall_passed,
        "queries":          [_serialise(q) for q in report.queries],
        "index_stats":      report.index_stats,
    }
    path = reports_dir / f"benchmark_report_{run_id}.json"
    path.write_bytes(orjson.dumps(out, option=orjson.OPT_INDENT_2))
    log.info("Benchmark report saved → {p}", p=path)

    _print_report(report)
    return report


def _print_report(report: BenchmarkReport) -> None:
    print()
    print("=" * 65)
    print("BENCHMARK REPORT")
    print("=" * 65)
    print(f"DB               : {report.db_version}")
    print(f"PostGIS          : {'Yes' if report.postgis_available else 'No (location queries skipped)'}")
    print(f"Stations         : {report.total_stations:,}")
    print(f"city_id NULLs    : {report.city_state_nulls:,}")
    print()
    print(f"{'Query':<25} {'Exec ms':>8} {'Target':>8} {'Plan type':<22} {'Status'}")
    print("-" * 75)
    for q in report.queries:
        status = "PASS" if q.passed else "FAIL ←"
        print(
            f"{q.name:<25} {q.execution_ms:>8.2f} {q.target_ms:>7.0f}ms"
            f" {q.plan_type:<22} {status}"
        )
    print()
    print(f"Overall: {'PASSED' if report.overall_passed else 'FAILED'} "
          f"({sum(q.passed for q in report.queries)}/{len(report.queries)} queries within target)")
    print()
    print("Index scan counts (stations table, ascending):")
    for row in report.index_stats:
        if row["table_name"] == "stations":
            print(f"  {row['index_name']:<45} scans={row['idx_scan']:>5}  {row['index_size']}")
    print("=" * 65)


def _parse_args(argv: list[str]) -> str | None:
    if "--run-id" in argv:
        idx = argv.index("--run-id")
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def main() -> None:
    run_id = _parse_args(sys.argv[1:]) or "benchmark"
    asyncio.run(run_benchmark(run_id, settings.reports_dir))


if __name__ == "__main__":
    main()
