"""
Pydantic models for all data structures returned by the Statiq APIs.

These models are the single source of truth for data shapes across the
entire scraper. Collectors, parsers, and storage all import from here.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# API response envelope (shared by all backend.statiq.co.in endpoints)
# ─────────────────────────────────────────────────────────────────────────────

class MetaResponse(BaseModel):
    status_code: int
    success: bool
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# Station markers — returned by POST /station/v1/markers
# ─────────────────────────────────────────────────────────────────────────────

class StationMarker(BaseModel):
    """
    One entry from the markers API response.
    Contains location and identity fields only — no charger/pricing detail.
    Those come from the station detail page (Step 4).
    """

    station_id: int = Field(..., gt=0, description="Statiq's internal station ID (primary key)")
    station_name: str = Field(..., description="Human-readable station name")
    address: str | None = Field(None, description="Street address; null for some private stations")
    latitude: float = Field(..., description="WGS-84 latitude")
    longitude: float = Field(..., description="WGS-84 longitude")
    map_pin_url: str | None = Field(None, description="Default map marker icon URL")
    focused_map_pin_url: str | None = Field(None, description="Selected/focused map marker icon URL")
    is_community_listed: int = Field(0, ge=0, le=1, description="1 if listed in community network")
    access_type: int = Field(..., description="1 = public, 2 = captive/private")

    # ── Field-level cleaning ─────────────────────────────────────────────────

    @field_validator("station_name", mode="before")
    @classmethod
    def clean_name(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError(f"station_name must be a string, got {type(v)}")
        stripped = v.strip()
        if not stripped:
            raise ValueError("station_name cannot be blank")
        return stripped

    @field_validator("address", mode="before")
    @classmethod
    def clean_address(cls, v: Any) -> str | None:
        if v is None:
            return None
        cleaned = str(v).strip()
        return cleaned if cleaned else None

    @field_validator("latitude", mode="before")
    @classmethod
    def validate_latitude(cls, v: Any) -> float:
        f = float(v)
        if not (-90.0 <= f <= 90.0):
            raise ValueError(f"latitude {f} is outside valid range [-90, 90]")
        return f

    @field_validator("longitude", mode="before")
    @classmethod
    def validate_longitude(cls, v: Any) -> float:
        f = float(v)
        if not (-180.0 <= f <= 180.0):
            raise ValueError(f"longitude {f} is outside valid range [-180, 180]")
        return f

    # ── Derived helpers (not serialised) ─────────────────────────────────────

    @property
    def is_public(self) -> bool:
        return self.access_type == 1

    @property
    def has_valid_coordinates(self) -> bool:
        """True when neither coordinate is zero (0,0 = null island — data error)."""
        return self.latitude != 0.0 and self.longitude != 0.0

    @property
    def operator_hint(self) -> str | None:
        """
        Heuristic: extract operator name from the map_pin_url CDN path.
        e.g. '.../charging-pin/Sunfuel+-+default.png' → 'Sunfuel'
        Used as a lightweight brand signal until the detail page is scraped.
        """
        url = self.map_pin_url or ""
        if "/charging-pin/" not in url:
            return None
        filename = url.rsplit("/", 1)[-1]
        # Strip extension and common suffixes
        name = filename.replace(".png", "").replace("-default", "").replace("+default", "")
        name = name.replace("+-+", " ").replace("+", " ").replace("-", " ").strip()
        return name if name else None


# ─────────────────────────────────────────────────────────────────────────────
# Markers API full response wrapper
# ─────────────────────────────────────────────────────────────────────────────

class MarkersData(BaseModel):
    country: str | None = None
    stations: list[StationMarker]


class MarkersAPIResponse(BaseModel):
    meta: MetaResponse
    data: MarkersData

    @model_validator(mode="after")
    def check_api_success(self) -> "MarkersAPIResponse":
        if not self.meta.success:
            raise ValueError(
                f"Markers API returned failure: status_code={self.meta.status_code} "
                f"message='{self.meta.message}'"
            )
        return self

    @property
    def stations(self) -> list[StationMarker]:
        return self.data.stations

    @property
    def station_count(self) -> int:
        return len(self.data.stations)


# ─────────────────────────────────────────────────────────────────────────────
# City list — returned by GET /station/v1/city_data
# ─────────────────────────────────────────────────────────────────────────────

class City(BaseModel):
    city_id: int = Field(..., gt=0)
    name: str
    latitude: float
    longitude: float


class CitiesAPIResponse(BaseModel):
    meta: MetaResponse
    data: list[City]

    @property
    def cities(self) -> list[City]:
        return self.data
