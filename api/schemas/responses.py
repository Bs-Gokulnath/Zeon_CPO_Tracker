from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator


_cfg = ConfigDict(from_attributes=True)


class _NaNAware(BaseModel):
    """Base model that coerces Decimal NaN → None before validation."""

    @model_validator(mode="before")
    @classmethod
    def _scrub_nan(cls, data):
        if isinstance(data, dict):
            return {
                k: (None if isinstance(v, Decimal) and v.is_nan() else v)
                for k, v in data.items()
            }
        return data


class ConnectorOut(_NaNAware):
    model_config = _cfg
    id:               int
    display_id:       int | None
    connector_type:   str | None
    connector_type_id: int | None
    availability:     bool | None
    connector_status: str | None
    error_message:    str | None
    connector_image:  str | None


class ChargerOut(_NaNAware):
    model_config = _cfg
    id:                        int
    charger_name:              str | None
    type:                      str | None
    power_rating_kw:           Decimal | None
    price:                     Decimal | None
    currency:                  str | None
    price_display:             str | None
    connector_count:           int
    available_connector_count: int
    connectors:                list[ConnectorOut] = []


class AmenityOut(_NaNAware):
    model_config = _cfg
    id:   int
    type: str
    icon: str | None


class NearbyStationOut(_NaNAware):
    model_config = _cfg
    nearby_station_id: int
    station_name:      str | None
    latitude:          Decimal | None
    longitude:         Decimal | None
    access_type:       int | None
    avg_review_rating: Decimal | None
    is_connected:      bool | None
    station_types:     str | None
    branding_logo:     str | None


class ReviewSummaryOut(_NaNAware):
    model_config = _cfg
    avg_rating:      Decimal | None
    review_count:    int
    rating_1_count:  int
    rating_2_count:  int
    rating_3_count:  int
    rating_4_count:  int
    rating_5_count:  int


class StationSummary(_NaNAware):
    model_config = _cfg
    id:                        int
    station_name:              str | None
    city_name_cached:          str | None
    operator_name_cached:      str | None
    latitude:                  Decimal | None
    longitude:                 Decimal | None
    availability:              str | None
    charger_type:              str | None
    highest_power_kw:          Decimal | None
    total_charger_count:       int
    available_connector_count: int
    avg_rating:                Decimal | None
    review_count:              int | None
    access_type:               str | None
    min_ac_price:              Decimal | None
    min_dc_price:              Decimal | None
    has_amenities:             bool
    scraped_at:                str | None


class StationDetail(_NaNAware):
    model_config = _cfg
    id:                        int
    station_name:              str | None
    # FK-resolved names
    city_name:                 str | None = None
    state_name:                str | None = None
    operator_name:             str | None = None
    # Cached denormalized names
    city_name_cached:          str | None
    operator_name_cached:      str | None
    # Location
    address:                   str | None
    area:                      str | None
    landmark:                  str | None
    latitude:                  Decimal | None
    longitude:                 Decimal | None
    # Operational
    access_type:               str | None
    availability:              str | None
    is_connected:              bool | None
    operational_time:          str | None
    charger_type:              str | None
    highest_power_kw:          Decimal | None
    # Counts
    ac_charger_count:          int
    dc_charger_count:          int
    total_charger_count:       int
    total_connector_count:     int
    available_connector_count: int
    # Pricing
    min_ac_price:              Decimal | None
    max_ac_price:              Decimal | None
    min_dc_price:              Decimal | None
    max_dc_price:              Decimal | None
    # Ratings
    avg_rating:                Decimal | None
    review_count:              int | None
    # Media
    has_amenities:             bool
    station_image_url:         str | None
    station_banner:            str | None
    navigation_link:           str | None
    scraped_at:                str | None
    run_id:                    str | None
    # Nested
    chargers:         list[ChargerOut] = []
    amenities:        list[AmenityOut] = []
    nearby_stations:  list[NearbyStationOut] = []
    review_summary:   ReviewSummaryOut | None = None


# ── Filter dropdown responses ─────────────────────────────────────────────────

class StateItem(BaseModel):
    model_config = _cfg
    id:   int
    name: str
    code: str | None


class CityItem(BaseModel):
    model_config = _cfg
    id:       int
    name:     str
    state_id: int


class OperatorItem(BaseModel):
    model_config = _cfg
    id:             int
    name:           str
    operator_type:  str | None


class ConnectorTypeItem(BaseModel):
    model_config = _cfg
    id:   int
    name: str | None


class MapPoint(BaseModel):
    """Lightweight coordinate-only response for map markers."""
    model_config = _cfg
    id:           int
    latitude:     Decimal | None
    longitude:    Decimal | None
    availability: str | None
    charger_type: str | None


class FiltersResponse(BaseModel):
    states:          list[StateItem]
    cities:          list[CityItem]
    operators:       list[OperatorItem]
    charger_types:   list[str]
    connector_types: list[ConnectorTypeItem]
    access_types:    list[str]
    price_range:     dict
    rating_buckets:  list[dict]


# ── Analytics responses ───────────────────────────────────────────────────────

class OverviewStats(_NaNAware):
    total_stations:            int
    available_stations:        int
    total_chargers:            int
    total_connectors:          int
    ac_stations:               int
    dc_stations:               int
    mixed_stations:            int
    avg_rating:                Decimal | None
    states_covered:            int
    cities_covered:            int
    operators_count:           int


class StateDistributionItem(_NaNAware):
    model_config = _cfg
    state_id:          int
    state_name:        str
    total_stations:    int
    available_stations: int
    dc_stations:       int
    ac_stations:       int
    mixed_stations:    int
    total_chargers:    int
    avg_rating:        Decimal | None


class CityDistributionItem(_NaNAware):
    model_config = _cfg
    city_id:           int
    city_name:         str
    state_name:        str
    total_stations:    int
    available_stations: int
    total_chargers:    int
    avg_rating:        Decimal | None


class OperatorDistributionItem(_NaNAware):
    model_config = _cfg
    operator_id:       int
    operator_name:     str
    operator_type:     str | None
    total_stations:    int
    available_stations: int
    dc_stations:       int
    ac_stations:       int
    total_chargers:    int
    avg_rating:        Decimal | None


class ChargerSpeedItem(_NaNAware):
    model_config = _cfg
    speed_category:  str
    charger_type:    str
    charger_count:   int
    avg_price:       Decimal | None
    min_power_kw:    Decimal | None
    max_power_kw:    Decimal | None


class AcDcBreakdown(_NaNAware):
    model_config = _cfg
    ac_stations:        int
    dc_stations:        int
    mixed_stations:     int
    total_ac_chargers:  int
    total_dc_chargers:  int
    avg_min_ac_price:   Decimal | None
    avg_min_dc_price:   Decimal | None
    avg_highest_power_kw: Decimal | None


# ── Search response ───────────────────────────────────────────────────────────

class SearchHit(BaseModel):
    id:           int
    station_name: str | None
    city_name:    str | None
    state_name:   str | None
    charger_type: str | None
    availability: str | None


# ── Nearby response ───────────────────────────────────────────────────────────

class NearbyResult(_NaNAware):
    id:                        int
    station_name:              str | None
    latitude:                  Decimal | None
    longitude:                 Decimal | None
    distance_km:               float
    availability:              str | None
    charger_type:              str | None
    highest_power_kw:          Decimal | None
    available_connector_count: int
    avg_rating:                Decimal | None
    access_type:               str | None


# ── Health responses ──────────────────────────────────────────────────────────

class HealthStatus(BaseModel):
    status:  str        # "ok" | "degraded" | "down"
    detail:  str | None = None


class HealthResponse(BaseModel):
    status:       str
    db:           HealthStatus
    cache:        HealthStatus
    etl_run_id:   str | None
    etl_age_hrs:  float | None
    stations:     int | None
