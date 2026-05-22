from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClosingStatus(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str
    text_color: str | None = None


class ConnectorType(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    connector_name: str
    connector_image_url: str | None = None


class Amenity(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    icon: str | None = None
    map_id: int | None = None
    id: int | None = None


class Connector(BaseModel):
    model_config = ConfigDict(extra="allow")

    display_id: int | None = None
    connector_id: int
    connector_type: str
    connector_image: str | None = None
    availability: bool
    error_message: str | None = None
    connector_type_id: int | None = None
    connector_status: str | None = None


class PluginDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    charger_id: int
    price_with_currency: str | None = None
    price: float | None = None
    currency: str | None = None
    symbol: str | None = None
    connectors: list[Connector] = []
    type: str | None = None
    power_rating: float | None = None
    charger_name: str | None = None
    last_used_on: str | None = None


class ReviewStats(BaseModel):
    model_config = ConfigDict(extra="allow")

    percentage_per_star: dict[str, int | float] = Field(default_factory=dict)


class NearbyStationType(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    bg_color: str | None = None
    text_color: str | None = None


class NearbyStation(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    station_name: str
    latitude: float
    longitude: float
    address: str | None = None
    area: str | None = None
    avg_review_rating: float | None = None
    navigation_link: str | None = None
    is_connected: bool | None = None
    station_type: list[NearbyStationType] = []
    access_type: int | None = None
    is_community_listed: bool | None = None
    branding_logo: str | None = None


class NearbyData(BaseModel):
    model_config = ConfigDict(extra="allow")

    cards: list[NearbyStation] = []


class StationDetail(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    station_id: int = Field(alias="id")
    station_name: str
    latitude: float
    longitude: float
    address: str | None = None
    area: str | None = None
    navigation_link: str | None = None
    closing_status: ClosingStatus | None = None
    total_distance: str | None = None
    operational_time: str | None = None
    connector_types: list[ConnectorType] = []
    avg_review_rating: float | None = None
    no_of_reviews: int | None = None
    station_image_url: str | None = None
    is_connected: bool | None = None
    station_banner: str | None = None
    landmark: str | None = None
    amenities_icon: list[Amenity] = []
    plugin_details: list[PluginDetail] = []
    review_stats: ReviewStats | None = None
    map_pin_url: str | None = None
    steps_to_reach: bool | str | None = None
    station_city_name: str | None = None
    station_access_type: str | None = None
    availability: str | None = None
    highest_power_rating: float | None = None
    charger_type_of_station: str | None = None
    station_images: list[Any] = []


class StationDetailResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    station_id: int
    station_detail: StationDetail | None = None
    nearby_stations: list[NearbyStation] = []
    ac_count: int = 0
    dc_count: int = 0
    ac_prices: list[float] = []
    dc_prices: list[float] = []
    scraped_at: str
    parse_success: bool
    missing_fields: list[str] = []
    coverage_pct: float = 0.0
