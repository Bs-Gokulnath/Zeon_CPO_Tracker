from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PageInfo(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class StationAggStats(BaseModel):
    total_stations:     int = 0
    available_stations: int = 0
    total_chargers:     int = 0
    total_connectors:   int = 0
    cities_covered:     int = 0
    operators_count:    int = 0


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data:  list[T]
    page:  PageInfo
    stats: StationAggStats = StationAggStats()


def make_page(
    data: list[T],
    total: int,
    page: int,
    page_size: int,
    stats: StationAggStats | None = None,
) -> PaginatedResponse[T]:
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    return PaginatedResponse(
        data=data,
        page=PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
        stats=stats or StationAggStats(),
    )
