"""Unit tests for scraper.config — validates settings load, types, and derived properties."""
import pytest

from scraper.config import ScraperSettings, get_settings


class TestScraperSettings:
    def test_defaults_load_without_env_file(self, tmp_path, monkeypatch):
        """Settings must initialise with sensible defaults even without a .env file."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Point env_file to a non-existent path so no file is loaded
        s = ScraperSettings(_env_file=tmp_path / ".env.nonexistent")
        assert s.scraper_concurrency == 50
        assert s.scraper_max_retries == 5
        assert s.log_level == "INFO"

    def test_log_level_is_uppercased(self, tmp_path):
        s = ScraperSettings(_env_file=tmp_path / ".env.nonexistent", log_level="debug")
        assert s.log_level == "DEBUG"

    def test_invalid_log_level_raises(self, tmp_path):
        with pytest.raises(Exception):
            ScraperSettings(_env_file=tmp_path / ".env.nonexistent", log_level="VERBOSE")

    def test_india_bbox_vertices_is_closed_polygon(self, tmp_path):
        s = ScraperSettings(_env_file=tmp_path / ".env.nonexistent")
        verts = s.india_bbox_vertices
        # Must have at least 5 points (API requirement)
        assert len(verts) >= 5
        # Must be a closed polygon (first == last)
        assert verts[0] == verts[-1]
        # Each vertex is [lon, lat]
        for v in verts:
            assert len(v) == 2
            lon, lat = v
            # Longitude within India range
            assert 68.0 <= lon <= 97.5
            # Latitude within India range
            assert 8.0 <= lat <= 37.0

    def test_freshness_ttl_in_seconds(self, tmp_path):
        s = ScraperSettings(
            _env_file=tmp_path / ".env.nonexistent",
            scraper_station_freshness_ttl_hours=24,
        )
        assert s.station_freshness_ttl_seconds == 86400

    def test_proxy_config_none_when_disabled(self, tmp_path):
        s = ScraperSettings(_env_file=tmp_path / ".env.nonexistent", proxy_enabled=False)
        assert s.proxy_config is None

    def test_proxy_config_dict_when_enabled(self, tmp_path):
        s = ScraperSettings(
            _env_file=tmp_path / ".env.nonexistent",
            proxy_enabled=True,
            proxy_url="http://proxy:8080",
        )
        cfg = s.proxy_config
        assert cfg is not None
        assert "https://" in cfg

    def test_directories_created_on_init(self, tmp_path):
        s = ScraperSettings(
            _env_file=tmp_path / ".env.nonexistent",
            raw_data_dir=tmp_path / "data" / "raw",
            failed_data_dir=tmp_path / "data" / "failed",
            log_dir=tmp_path / "logs",
        )
        assert s.raw_data_dir.exists()
        assert s.failed_data_dir.exists()
        assert s.log_dir.exists()

    def test_get_settings_returns_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
