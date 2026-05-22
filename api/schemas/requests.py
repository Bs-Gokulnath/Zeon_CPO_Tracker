from __future__ import annotations

from enum import Enum

from fastapi import Query
from pydantic import BaseModel, Field


class SortBy(str, Enum):
    rating          = "rating"
    power           = "power"
    price_asc       = "price_asc"
    price_desc      = "price_desc"
    connector_count = "connector_count"
    charger_count   = "charger_count"
    name            = "name"
    id              = "id"


class StationFilters(BaseModel):
    # ── Multi-value (IN clause) ────────────────────────────────────────────────
    state_id:          list[int] = Field(default_factory=list)
    city_id:           list[int] = Field(default_factory=list)
    operator_id:       list[int] = Field(default_factory=list)
    charger_type:      list[str] = Field(default_factory=list)
    access_type:       list[str] = Field(default_factory=list)
    # ── Single-value ──────────────────────────────────────────────────────────
    connector_type_id: int | None   = None
    availability:      str | None   = None
    min_kw:            float | None = None
    max_kw:            float | None = None
    min_price:         float | None = None
    max_price:         float | None = None
    min_rating:        float | None = None
    has_amenities:     bool | None  = None
    q:                 str | None   = None
    sort_by:           SortBy = SortBy.id
    page:              int = Field(1, ge=1)
    page_size:         int = Field(50, ge=1, le=200)


class NearbyParams(BaseModel):
    lat:          float = Field(..., ge=-90, le=90)
    lon:          float = Field(..., ge=-180, le=180)
    radius_km:    float = Field(5.0, gt=0, le=100)
    charger_type: str | None = None
    limit:        int = Field(20, ge=1, le=100)


class SearchParams(BaseModel):
    q:     str = Field(..., min_length=1, max_length=100)
    limit: int = Field(10, ge=1, le=50)
