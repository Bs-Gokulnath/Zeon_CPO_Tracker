"""
Statiq EV Charging Station Scraper
===================================
Entry point:  python -m scraper.pipeline  (or the `scrape` CLI script)
"""
from scraper.config import settings
from scraper.utils.logger import configure_logging

# Configure logging as soon as the package is imported.
# Any module that does `from scraper.utils.logger import logger`
# will get the already-configured instance.
configure_logging(log_dir=settings.log_dir, log_level=settings.log_level)
