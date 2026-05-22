from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Audit / orchestration ─────────────────────────────────────────────────────

class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    run_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_stations: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_report: Mapped[Optional[dict]] = mapped_column(JSONB)

    stations: Mapped[list[Station]] = relationship(back_populates="scrape_run")
    failed_scrapes: Mapped[list[FailedScrape]] = relationship(back_populates="scrape_run")
    status_history: Mapped[list[StationStatusHistory]] = relationship(
        back_populates="scrape_run"
    )


class FailedScrape(Base):
    __tablename__ = "failed_scrapes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scrape_runs.run_id"))
    station_id: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    scrape_run: Mapped[Optional[ScrapeRun]] = relationship(back_populates="failed_scrapes")


# ── Geography dimension tables ────────────────────────────────────────────────

class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(10))

    cities: Mapped[list[City]] = relationship(back_populates="state")
    stations: Mapped[list[Station]] = relationship(back_populates="state")


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)

    __table_args__ = (UniqueConstraint("name", "state_id", name="uq_cities_name_state"),)

    state: Mapped[State] = relationship(back_populates="cities")
    stations: Mapped[list[Station]] = relationship(back_populates="city")


# ── Operator dimension table ──────────────────────────────────────────────────

class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 'EV_NETWORK' | 'FUEL_RETAIL' | 'HOSPITALITY' | 'OTHER'
    operator_type: Mapped[Optional[str]] = mapped_column(String(50))
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    stations: Mapped[list[Station]] = relationship(back_populates="operator")


# ── Charger / connector dimension tables ──────────────────────────────────────

class ConnectorType(Base):
    __tablename__ = "connector_types"

    # Statiq's connector_type_id is the natural key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connector_name: Mapped[Optional[str]] = mapped_column(String(100))
    connector_image_url: Mapped[Optional[str]] = mapped_column(Text)

    connectors: Mapped[list[Connector]] = relationship(back_populates="connector_type_ref")


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(Text)

    station_amenities: Mapped[list[StationAmenity]] = relationship(back_populates="amenity")


# ── Core fact table ───────────────────────────────────────────────────────────

class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Statiq station_id
    station_name: Mapped[Optional[str]] = mapped_column(String(500))

    city_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cities.id"))
    state_id: Mapped[Optional[int]] = mapped_column(ForeignKey("states.id"))
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("operators.id"))

    # Denormalized for the search_vector trigger (avoids cross-table references)
    city_name_cached: Mapped[Optional[str]] = mapped_column(String(200))
    operator_name_cached: Mapped[Optional[str]] = mapped_column(String(200))

    address: Mapped[Optional[str]] = mapped_column(Text)
    area: Mapped[Optional[str]] = mapped_column(String(500))
    landmark: Mapped[Optional[str]] = mapped_column(String(500))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    # PostGIS geography column — populated from lat/lon by ETL
    location: Mapped[Optional[str]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    # 'public' | 'captive'
    access_type: Mapped[Optional[str]] = mapped_column(String(20))
    # 'Available' | 'Unavailable' | 'Available in'
    availability: Mapped[Optional[str]] = mapped_column(String(30))
    is_connected: Mapped[Optional[bool]] = mapped_column(Boolean)
    operational_time: Mapped[Optional[str]] = mapped_column(String(200))
    # 'AC' | 'DC' | 'Mixed'
    charger_type: Mapped[Optional[str]] = mapped_column(String(10))
    highest_power_kw: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    avg_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    review_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Pre-aggregated counts (updated by ETL, avoids joins on every dashboard request)
    ac_charger_count: Mapped[int] = mapped_column(Integer, default=0)
    dc_charger_count: Mapped[int] = mapped_column(Integer, default=0)
    total_charger_count: Mapped[int] = mapped_column(Integer, default=0)
    total_connector_count: Mapped[int] = mapped_column(Integer, default=0)
    available_connector_count: Mapped[int] = mapped_column(Integer, default=0)

    min_ac_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    max_ac_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    min_dc_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    max_dc_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    has_amenities: Mapped[bool] = mapped_column(Boolean, default=False)
    station_image_url: Mapped[Optional[str]] = mapped_column(Text)
    station_banner: Mapped[Optional[str]] = mapped_column(Text)
    navigation_link: Mapped[Optional[str]] = mapped_column(Text)

    # Auto-updated by trg_station_search_vector — do not set manually
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)

    scraped_at: Mapped[Optional[str]] = mapped_column(String(50))  # ISO8601 from scraper
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scrape_runs.run_id"))

    scrape_run: Mapped[Optional[ScrapeRun]] = relationship(back_populates="stations")
    city: Mapped[Optional[City]] = relationship(back_populates="stations")
    state: Mapped[Optional[State]] = relationship(back_populates="stations")
    operator: Mapped[Optional[Operator]] = relationship(back_populates="stations")
    chargers: Mapped[list[Charger]] = relationship(back_populates="station")
    connectors: Mapped[list[Connector]] = relationship(back_populates="station")
    station_amenities: Mapped[list[StationAmenity]] = relationship(back_populates="station")
    nearby_stations: Mapped[list[NearbyStation]] = relationship(back_populates="source_station")
    reviews_summary: Mapped[Optional[ReviewsSummary]] = relationship(
        back_populates="station", uselist=False
    )
    status_history: Mapped[list[StationStatusHistory]] = relationship(back_populates="station")


# ── Charger / connector fact tables ──────────────────────────────────────────

class Charger(Base):
    __tablename__ = "chargers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Statiq charger_id
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    charger_name: Mapped[Optional[str]] = mapped_column(String(200))
    type: Mapped[Optional[str]] = mapped_column(String(10))  # 'AC' | 'DC'
    power_rating_kw: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    price_display: Mapped[Optional[str]] = mapped_column(String(100))
    last_used_on: Mapped[Optional[str]] = mapped_column(String(100))
    connector_count: Mapped[int] = mapped_column(Integer, default=0)
    available_connector_count: Mapped[int] = mapped_column(Integer, default=0)

    station: Mapped[Station] = relationship(back_populates="chargers")
    connectors: Mapped[list[Connector]] = relationship(back_populates="charger")


class Connector(Base):
    __tablename__ = "connectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Statiq connector_id
    charger_id: Mapped[int] = mapped_column(ForeignKey("chargers.id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    display_id: Mapped[Optional[int]] = mapped_column(Integer)
    connector_type: Mapped[Optional[str]] = mapped_column(String(100))
    connector_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("connector_types.id"), nullable=True
    )
    availability: Mapped[Optional[bool]] = mapped_column(Boolean)
    connector_status: Mapped[Optional[str]] = mapped_column(String(100))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    connector_image: Mapped[Optional[str]] = mapped_column(Text)

    charger: Mapped[Charger] = relationship(back_populates="connectors")
    station: Mapped[Station] = relationship(back_populates="connectors")
    connector_type_ref: Mapped[Optional[ConnectorType]] = relationship(
        back_populates="connectors"
    )


# ── Junction / satellite tables ───────────────────────────────────────────────

class StationAmenity(Base):
    __tablename__ = "station_amenities"

    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), primary_key=True)
    amenity_id: Mapped[int] = mapped_column(ForeignKey("amenities.id"), primary_key=True)
    map_id: Mapped[Optional[int]] = mapped_column(Integer)

    station: Mapped[Station] = relationship(back_populates="station_amenities")
    amenity: Mapped[Amenity] = relationship(back_populates="station_amenities")


class NearbyStation(Base):
    __tablename__ = "nearby_stations"

    source_station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id"), primary_key=True
    )
    # Not an FK — nearby stations may not be in our scraped set
    nearby_station_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_name: Mapped[Optional[str]] = mapped_column(String(500))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    access_type: Mapped[Optional[int]] = mapped_column(Integer)  # 1=public, 2=captive
    avg_review_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    is_connected: Mapped[Optional[bool]] = mapped_column(Boolean)
    station_types: Mapped[Optional[str]] = mapped_column(String(200))
    branding_logo: Mapped[Optional[str]] = mapped_column(Text)

    source_station: Mapped[Station] = relationship(back_populates="nearby_stations")


class ReviewsSummary(Base):
    __tablename__ = "reviews_summary"

    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), primary_key=True)
    avg_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_1_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_2_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_3_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_4_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_5_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    station: Mapped[Station] = relationship(back_populates="reviews_summary")


class StationStatusHistory(Base):
    __tablename__ = "station_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    scrape_run_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("scrape_runs.run_id"), nullable=True
    )
    availability: Mapped[Optional[str]] = mapped_column(String(30))
    available_connector_count: Mapped[Optional[int]] = mapped_column(Integer)
    avg_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    review_count: Mapped[Optional[int]] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    station: Mapped[Station] = relationship(back_populates="status_history")
    scrape_run: Mapped[Optional[ScrapeRun]] = relationship(back_populates="status_history")
