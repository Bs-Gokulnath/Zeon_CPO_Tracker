"""
Unit tests for scraper/parsers/schemas.py.

Tests field validation, cleaning, model_validators, and derived properties.
No network calls — all data is synthetic.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from scraper.parsers.schemas import (
    CitiesAPIResponse,
    City,
    MarkersAPIResponse,
    MarkersData,
    MetaResponse,
    StationMarker,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_marker(**overrides) -> dict:
    base = {
        "station_id": 1,
        "station_name": "Test Station",
        "address": "123 Main St",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "map_pin_url": "https://cdn/charging-pin/Tata+-+default.png",
        "focused_map_pin_url": None,
        "is_community_listed": 0,
        "access_type": 1,
    }
    base.update(overrides)
    return base


def _make_markers_response(stations: list[dict]) -> dict:
    return {
        "meta": {"status_code": 200, "success": True, "message": "OK"},
        "data": {"country": "India", "stations": stations},
    }


# ─────────────────────────────────────────────────────────────────────────────
# StationMarker — field validation
# ─────────────────────────────────────────────────────────────────────────────

class TestStationMarker:
    def test_valid_marker_parses(self):
        m = StationMarker(**_make_marker())
        assert m.station_id == 1
        assert m.station_name == "Test Station"
        assert m.latitude == pytest.approx(12.9716)

    def test_station_name_stripped(self):
        m = StationMarker(**_make_marker(station_name="  Padded Name  "))
        assert m.station_name == "Padded Name"

    def test_blank_station_name_raises(self):
        with pytest.raises(ValidationError, match="cannot be blank"):
            StationMarker(**_make_marker(station_name="   "))

    def test_non_string_station_name_raises(self):
        with pytest.raises(ValidationError):
            StationMarker(**_make_marker(station_name=42))

    def test_address_stripped(self):
        m = StationMarker(**_make_marker(address="  Road Name  "))
        assert m.address == "Road Name"

    def test_blank_address_becomes_none(self):
        m = StationMarker(**_make_marker(address="   "))
        assert m.address is None

    def test_null_address_allowed(self):
        m = StationMarker(**_make_marker(address=None))
        assert m.address is None

    def test_latitude_out_of_range_raises(self):
        with pytest.raises(ValidationError, match="outside valid range"):
            StationMarker(**_make_marker(latitude=91.0))

    def test_longitude_out_of_range_raises(self):
        with pytest.raises(ValidationError, match="outside valid range"):
            StationMarker(**_make_marker(longitude=-181.0))

    def test_station_id_must_be_positive(self):
        with pytest.raises(ValidationError):
            StationMarker(**_make_marker(station_id=0))

    def test_is_community_listed_default_zero(self):
        data = _make_marker()
        del data["is_community_listed"]
        m = StationMarker(**data)
        assert m.is_community_listed == 0

    def test_is_community_listed_rejects_invalid(self):
        with pytest.raises(ValidationError):
            StationMarker(**_make_marker(is_community_listed=2))


# ─────────────────────────────────────────────────────────────────────────────
# StationMarker — derived properties
# ─────────────────────────────────────────────────────────────────────────────

class TestStationMarkerProperties:
    def test_is_public_true_for_access_type_1(self):
        m = StationMarker(**_make_marker(access_type=1))
        assert m.is_public is True

    def test_is_public_false_for_access_type_2(self):
        m = StationMarker(**_make_marker(access_type=2))
        assert m.is_public is False

    def test_has_valid_coordinates_true(self):
        m = StationMarker(**_make_marker(latitude=12.9716, longitude=77.5946))
        assert m.has_valid_coordinates is True

    def test_has_valid_coordinates_false_when_zero_lat(self):
        m = StationMarker(**_make_marker(latitude=0.0, longitude=77.5946))
        assert m.has_valid_coordinates is False

    def test_has_valid_coordinates_false_when_zero_lon(self):
        m = StationMarker(**_make_marker(latitude=12.9716, longitude=0.0))
        assert m.has_valid_coordinates is False

    def test_operator_hint_extracted_from_url(self):
        url = "https://cdn.statiq.in/charging-pin/Sunfuel+-+default.png"
        m = StationMarker(**_make_marker(map_pin_url=url))
        assert m.operator_hint == "Sunfuel"

    def test_operator_hint_none_when_no_pin_url(self):
        m = StationMarker(**_make_marker(map_pin_url=None))
        assert m.operator_hint is None

    def test_operator_hint_none_for_unrecognised_url(self):
        m = StationMarker(**_make_marker(map_pin_url="https://cdn.example.com/other.png"))
        assert m.operator_hint is None

    def test_operator_hint_tata(self):
        url = "https://cdn/charging-pin/Tata+-+default.png"
        m = StationMarker(**_make_marker(map_pin_url=url))
        assert m.operator_hint == "Tata"


# ─────────────────────────────────────────────────────────────────────────────
# MarkersAPIResponse — model_validator and properties
# ─────────────────────────────────────────────────────────────────────────────

class TestMarkersAPIResponse:
    def test_valid_response_parses(self):
        raw = _make_markers_response([_make_marker()])
        resp = MarkersAPIResponse.model_validate(raw)
        assert resp.station_count == 1

    def test_stations_property_returns_list(self):
        raw = _make_markers_response([_make_marker(station_id=1), _make_marker(station_id=2)])
        resp = MarkersAPIResponse.model_validate(raw)
        assert len(resp.stations) == 2

    def test_api_failure_raises(self):
        raw = {
            "meta": {"status_code": 500, "success": False, "message": "Internal error"},
            "data": {"country": "India", "stations": []},
        }
        with pytest.raises(ValidationError, match="failure"):
            MarkersAPIResponse.model_validate(raw)

    def test_empty_stations_list_allowed(self):
        raw = _make_markers_response([])
        resp = MarkersAPIResponse.model_validate(raw)
        assert resp.station_count == 0

    def test_country_nullable(self):
        raw = _make_markers_response([])
        raw["data"]["country"] = None
        resp = MarkersAPIResponse.model_validate(raw)
        assert resp.data.country is None


# ─────────────────────────────────────────────────────────────────────────────
# CitiesAPIResponse
# ─────────────────────────────────────────────────────────────────────────────

class TestCitiesAPIResponse:
    def test_valid_cities_response(self):
        raw = {
            "meta": {"status_code": 200, "success": True, "message": "OK"},
            "data": [
                {"city_id": 1, "name": "Bengaluru", "latitude": 12.97, "longitude": 77.59},
                {"city_id": 2, "name": "Mumbai", "latitude": 19.07, "longitude": 72.87},
            ],
        }
        resp = CitiesAPIResponse.model_validate(raw)
        assert len(resp.cities) == 2
        assert resp.cities[0].name == "Bengaluru"

    def test_city_id_must_be_positive(self):
        with pytest.raises(ValidationError):
            City(city_id=0, name="X", latitude=0.0, longitude=0.0)
