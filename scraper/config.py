from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root — one level above this file
ROOT_DIR = Path(__file__).resolve().parent.parent


class ScraperSettings(BaseSettings):
    """
    All runtime configuration, loaded from environment variables / .env file.
    Validated at import time — bad config raises immediately, not mid-run.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/statiq_db",
        description="Async PostgreSQL connection string (used by SQLAlchemy async engine)",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://postgres:password@localhost:5432/statiq_db",
        description="Sync PostgreSQL connection string (used by Alembic migrations)",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
    )

    # ── Concurrency & timing ──────────────────────────────────────────────────
    scraper_concurrency: Annotated[int, Field(ge=1, le=200)] = Field(
        default=50,
        description="Maximum simultaneous HTTP connections to statiq.in",
    )
    scraper_rate_limit_per_minute: Annotated[int, Field(ge=1, le=500)] = Field(
        default=80,
        description="Max requests/minute to statiq.in detail pages",
    )
    scraper_api_rate_limit_per_minute: Annotated[int, Field(ge=1, le=100)] = Field(
        default=10,
        description="Max requests/minute to backend.statiq.co.in",
    )
    scraper_request_timeout: Annotated[int, Field(ge=5, le=120)] = Field(
        default=30,
        description="HTTP request timeout in seconds",
    )
    scraper_max_retries: Annotated[int, Field(ge=0, le=10)] = Field(
        default=5,
        description="Maximum retry attempts per failed request",
    )

    # ── Storage ───────────────────────────────────────────────────────────────
    store_raw_rsc: bool = Field(
        default=True,
        description="Whether to persist raw RSC payload files",
    )
    compress_raw_rsc: bool = Field(
        default=True,
        description="If True, raw RSC payloads are saved as .txt.gz instead of .txt",
    )

    # ── Batch processing ──────────────────────────────────────────────────────
    scraper_batch_size: Annotated[int, Field(ge=10, le=1000)] = Field(
        default=250,
        description="Number of stations per batch",
    )
    scraper_batch_jitter_min: float = Field(
        default=2.0,
        description="Minimum seconds to sleep between batches",
    )
    scraper_batch_jitter_max: float = Field(
        default=5.0,
        description="Maximum seconds to sleep between batches",
    )

    # ── Freshness / incremental ───────────────────────────────────────────────
    scraper_station_freshness_ttl_hours: Annotated[int, Field(ge=1)] = Field(
        default=24,
        description="Hours before a successfully scraped station is re-scraped",
    )
    scraper_city_cache_ttl_days: Annotated[int, Field(ge=1)] = Field(
        default=7,
        description="Days before the city list Redis cache expires",
    )

    # ── Statiq API endpoints ──────────────────────────────────────────────────
    statiq_base_url: str = Field(
        default="https://www.statiq.in",
        description="Statiq website base URL (for station detail pages)",
    )
    statiq_markers_url: str = Field(
        default="https://backend.statiq.co.in/station/v1/markers",
        description="Markers API — returns all stations within a bounding polygon",
    )
    statiq_cities_url: str = Field(
        default="https://backend.statiq.co.in/station/v1/city_data",
        description="City list API",
    )

    # India bounding box stored as "lon_west,lat_north,lon_east,lat_south"
    statiq_india_bbox: str = Field(
        default="68.0,37.0,97.5,8.0",
        description="Bounding box covering all of India: lon_west,lat_north,lon_east,lat_south",
    )

    # ── Markers API timeout (India-wide call verified at 56–63s in Step 2) ───
    scraper_markers_timeout: Annotated[int, Field(ge=30, le=180)] = Field(
        default=90,
        description="Read timeout for the markers API call (India bbox takes ~60s)",
    )

    # ── Output paths ─────────────────────────────────────────────────────────
    raw_data_dir: Path = Field(default=ROOT_DIR / "data" / "raw")
    processed_data_dir: Path = Field(default=ROOT_DIR / "data" / "processed")
    exports_dir: Path = Field(default=ROOT_DIR / "data" / "exports")
    failed_data_dir: Path = Field(default=ROOT_DIR / "data" / "failed")
    log_dir: Path = Field(default=ROOT_DIR / "logs")
    checkpoint_file: Path = Field(default=ROOT_DIR / "logs" / "checkpoint.json")
    checkpoints_dir: Path = Field(default=ROOT_DIR / "data" / "checkpoints")
    final_data_dir: Path = Field(default=ROOT_DIR / "data" / "final")
    reports_dir: Path = Field(default=ROOT_DIR / "reports")

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Proxy ─────────────────────────────────────────────────────────────────
    proxy_enabled: bool = Field(default=False)
    proxy_url: str | None = Field(default=None)
    proxy_rotation_enabled: bool = Field(default=False)

    # ── Playwright ────────────────────────────────────────────────────────────
    playwright_fallback_enabled: bool = Field(default=True)
    playwright_headless: bool = Field(default=True)

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return upper

    @model_validator(mode="after")
    def ensure_directories_exist(self) -> "ScraperSettings":
        for path in (
            self.raw_data_dir,
            self.processed_data_dir,
            self.exports_dir,
            self.failed_data_dir,
            self.log_dir,
            self.checkpoints_dir,
            self.final_data_dir,
            self.reports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def india_bbox_vertices(self) -> list[list[float]]:
        """
        Returns the India bounding box as a closed polygon in [lon, lat] format,
        ready to pass directly to the Statiq markers API 'vertices' field.

        The API requires minimum 5 points (closed polygon: first == last).
        Coordinate order: [longitude, latitude] — standard GeoJSON convention.
        """
        lon_w, lat_n, lon_e, lat_s = (float(x) for x in self.statiq_india_bbox.split(","))
        return [
            [lon_w, lat_n],  # NW corner
            [lon_e, lat_n],  # NE corner
            [lon_e, lat_s],  # SE corner
            [lon_w, lat_s],  # SW corner
            [lon_w, lat_n],  # close the polygon (repeat first point)
        ]

    @property
    def station_freshness_ttl_seconds(self) -> int:
        return self.scraper_station_freshness_ttl_hours * 3600

    @property
    def city_cache_ttl_seconds(self) -> int:
        return self.scraper_city_cache_ttl_days * 86400

    @property
    def proxy_config(self) -> dict | None:
        """Returns httpx-compatible proxy dict, or None if proxies are disabled."""
        if not self.proxy_enabled or not self.proxy_url:
            return None
        return {"http://": self.proxy_url, "https://": self.proxy_url}


@lru_cache(maxsize=1)
def get_settings() -> ScraperSettings:
    """
    Returns the singleton settings instance.
    Cached after first call — safe to import anywhere without re-reading .env.
    """
    return ScraperSettings()


# Module-level alias for ergonomic imports:  from scraper.config import settings
settings = get_settings()
