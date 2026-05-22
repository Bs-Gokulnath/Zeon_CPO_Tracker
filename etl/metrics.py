from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import orjson

from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.metrics")


@dataclass
class ETLMetrics:
    run_id: str
    # Phase timings (seconds)
    extract_secs: float = 0.0
    transform_secs: float = 0.0
    staging_secs: float = 0.0
    load_secs: float = 0.0
    mv_refresh_secs: float = 0.0
    validation_secs: float = 0.0
    total_secs: float = 0.0
    # Extract counts
    stations_extracted: int = 0
    chargers_extracted: int = 0
    connectors_extracted: int = 0
    amenities_extracted: int = 0
    nearby_extracted: int = 0
    connector_types_extracted: int = 0
    extract_errors: int = 0
    extract_warnings: int = 0
    # Dimension upserts
    states_upserted: int = 0
    cities_upserted: int = 0
    operators_upserted: int = 0
    connector_types_upserted: int = 0
    amenities_upserted: int = 0
    # Fact inserts / updates
    stations_inserted: int = 0
    stations_updated: int = 0
    stations_skipped: int = 0
    chargers_upserted: int = 0
    connectors_upserted: int = 0
    station_amenities_upserted: int = 0
    nearby_upserted: int = 0
    reviews_upserted: int = 0
    history_inserted: int = 0
    # Performance
    rows_per_sec: float = 0.0

    def total_rows_loaded(self) -> int:
        return (
            self.stations_inserted
            + self.stations_updated
            + self.chargers_upserted
            + self.connectors_upserted
            + self.nearby_upserted
        )

    def compute_derived(self) -> None:
        if self.total_secs > 0:
            self.rows_per_sec = round(self.total_rows_loaded() / self.total_secs, 1)


def save_etl_metrics(metrics: ETLMetrics, reports_dir: Path) -> Path:
    metrics.compute_derived()
    path = reports_dir / f"etl_metrics_{metrics.run_id}.json"
    path.write_bytes(orjson.dumps(asdict(metrics), option=orjson.OPT_INDENT_2))
    log.info("ETL metrics saved -> {p}", p=path)
    return path
