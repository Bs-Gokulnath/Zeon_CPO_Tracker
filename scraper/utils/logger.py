"""
Centralised logging configuration using loguru.

Usage:
    from scraper.utils.logger import logger, get_scrape_logger

    logger.info("Starting scraper run")
    logger.warning("Rate limit hit, backing off", station_id=1234)
    logger.error("Request failed", url=url, attempt=3)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger as _loguru_logger

if TYPE_CHECKING:
    from loguru import Logger


def _json_serializer(record: dict) -> str:
    """
    Custom orjson-based serializer for structured log files.
    Falls back to loguru's default if orjson is unavailable.
    """
    try:
        import orjson

        payload = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            **record["extra"],
        }
        if record["exception"]:
            payload["exception"] = str(record["exception"])
        return orjson.dumps(payload).decode() + "\n"
    except Exception:
        return record["message"] + "\n"


def configure_logging(
    log_dir: Path,
    log_level: str = "INFO",
    *,
    rotation: str = "50 MB",
    retention: str = "14 days",
) -> "Logger":
    """
    Configures loguru with three handlers:

    1. stderr  — colorized, human-readable, INFO+ (console progress)
    2. file    — rotating JSON, DEBUG+ (full audit trail)
    3. errors  — rotating JSON, ERROR+ (failures quick-access)

    Called once at startup from pipeline.py.
    Returns the configured logger for convenience.
    """
    _loguru_logger.remove()  # remove loguru's default stderr handler

    # ── Handler 1: Console ────────────────────────────────────────────────────
    _loguru_logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=True,
    )

    # ── Handler 2: Rotating JSON log (full audit) ─────────────────────────────
    _loguru_logger.add(
        log_dir / "scraper_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation=rotation,
        retention=retention,
        compression="gz",
        serialize=True,         # loguru's built-in JSON serialisation
        backtrace=True,
        diagnose=False,         # avoid leaking sensitive data in prod
        enqueue=True,           # async-safe: log calls don't block the event loop
    )

    # ── Handler 3: Errors-only log (quick triage) ─────────────────────────────
    _loguru_logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression="gz",
        serialize=True,
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    return _loguru_logger


def get_scrape_logger(name: str) -> "Logger":
    """
    Returns a logger bound with a module context label.
    Useful for per-module contextual logs without repeating boilerplate.

    Example:
        log = get_scrape_logger("station_list")
        log.info("Fetched {count} stations", count=6445)
    """
    return _loguru_logger.bind(scraper_module=name)


# Module-level alias — import this everywhere:  from scraper.utils.logger import logger
logger = _loguru_logger
