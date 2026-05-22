from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import orjson
import pandas as pd

from scraper.models.station_detail import StationDetailResult
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("pipeline.normalizer")


@dataclass
class NormalizedTables:
    stations: list[dict]
    chargers: list[dict]
    connectors: list[dict]
    amenities: list[dict]
    nearby_stations: list[dict]
    connector_types: list[dict]


def normalize(results: list[StationDetailResult]) -> NormalizedTables:
    """
    Convert a list of StationDetailResult into flat relational tables.
    Skips results where parse_success=False or station_detail is None.
    """
    stations: list[dict] = []
    chargers: list[dict] = []
    connectors: list[dict] = []
    amenities: list[dict] = []
    nearby_stations: list[dict] = []
    connector_types: list[dict] = []

    for result in results:
        if not result.parse_success or result.station_detail is None:
            continue

        sd = result.station_detail

        # ── Station record ────────────────────────────────────────────────────
        stations.append(
            {
                "station_id": sd.station_id,
                "station_name": sd.station_name,
                "city": sd.station_city_name,
                "address": sd.address,
                "area": sd.area,
                "landmark": sd.landmark,
                "latitude": sd.latitude,
                "longitude": sd.longitude,
                "access_type": sd.station_access_type,
                "availability": sd.availability,
                "is_connected": sd.is_connected,
                "operational_time": sd.operational_time,
                "charger_type": sd.charger_type_of_station,
                "highest_power_kw": sd.highest_power_rating,
                "avg_rating": sd.avg_review_rating,
                "review_count": sd.no_of_reviews,
                "ac_charger_count": result.ac_count,
                "dc_charger_count": result.dc_count,
                "total_charger_count": len(sd.plugin_details),
                "total_connector_count": sum(len(p.connectors) for p in sd.plugin_details),
                "available_connector_count": sum(
                    1
                    for p in sd.plugin_details
                    for c in p.connectors
                    if c.availability
                ),
                "min_ac_price": min(result.ac_prices) if result.ac_prices else None,
                "max_ac_price": max(result.ac_prices) if result.ac_prices else None,
                "min_dc_price": min(result.dc_prices) if result.dc_prices else None,
                "max_dc_price": max(result.dc_prices) if result.dc_prices else None,
                "has_amenities": len(sd.amenities_icon) > 0,
                "amenity_types": ",".join(a.type for a in sd.amenities_icon),
                "station_image_url": sd.station_image_url,
                "station_banner": sd.station_banner,
                "navigation_link": sd.navigation_link,
                "scraped_at": result.scraped_at,
            }
        )

        # ── Charger records ───────────────────────────────────────────────────
        for plugin in sd.plugin_details:
            chargers.append(
                {
                    "charger_id": plugin.charger_id,
                    "station_id": sd.station_id,
                    "charger_name": plugin.charger_name,
                    "type": plugin.type,
                    "power_rating_kw": plugin.power_rating,
                    "price": plugin.price,
                    "currency": plugin.currency,
                    "symbol": plugin.symbol,
                    "price_display": plugin.price_with_currency,
                    "last_used_on": plugin.last_used_on,
                    "connector_count": len(plugin.connectors),
                    "available_connector_count": sum(
                        1 for c in plugin.connectors if c.availability
                    ),
                }
            )

            # ── Connector records ─────────────────────────────────────────────
            for conn in plugin.connectors:
                connectors.append(
                    {
                        "connector_id": conn.connector_id,
                        "charger_id": plugin.charger_id,
                        "station_id": sd.station_id,
                        "display_id": conn.display_id,
                        "connector_type": conn.connector_type,
                        "connector_type_id": conn.connector_type_id,
                        "availability": conn.availability,
                        "connector_status": conn.connector_status,
                        "error_message": conn.error_message,
                        "connector_image": conn.connector_image,
                    }
                )

        # ── Amenity records ───────────────────────────────────────────────────
        for amenity in sd.amenities_icon:
            amenities.append(
                {
                    "amenity_id": amenity.id,
                    "station_id": sd.station_id,
                    "type": amenity.type,
                    "icon": amenity.icon,
                    "map_id": amenity.map_id,
                }
            )

        # ── Nearby station records ────────────────────────────────────────────
        for nearby in result.nearby_stations:
            nearby_stations.append(
                {
                    "source_station_id": result.station_id,
                    "nearby_station_id": nearby.id,
                    "station_name": nearby.station_name,
                    "latitude": nearby.latitude,
                    "longitude": nearby.longitude,
                    "access_type": nearby.access_type,
                    "avg_review_rating": nearby.avg_review_rating,
                    "is_connected": nearby.is_connected,
                    "station_types": ",".join(st.type for st in nearby.station_type),
                    "branding_logo": nearby.branding_logo,
                }
            )

        # ── ConnectorType records ─────────────────────────────────────────────
        for ct in sd.connector_types:
            connector_types.append(
                {
                    "station_id": sd.station_id,
                    "connector_type_id": ct.id,
                    "connector_name": ct.connector_name,
                    "connector_image_url": ct.connector_image_url,
                }
            )

    return NormalizedTables(
        stations=stations,
        chargers=chargers,
        connectors=connectors,
        amenities=amenities,
        nearby_stations=nearby_stations,
        connector_types=connector_types,
    )


def save_normalized_tables(
    tables: NormalizedTables,
    final_dir: Path,
    all_results: list[StationDetailResult],
) -> dict[str, Path]:
    """
    Persist all normalized tables as both JSON and CSV.
    Also writes stations_master.json with full model dumps for successful results.
    Returns a dict mapping table name -> canonical JSON path.
    """
    final_dir.mkdir(parents=True, exist_ok=True)

    table_map: dict[str, list[dict]] = {
        "stations": tables.stations,
        "chargers": tables.chargers,
        "connectors": tables.connectors,
        "amenities": tables.amenities,
        "nearby_stations": tables.nearby_stations,
        "connector_types": tables.connector_types,
    }

    output_paths: dict[str, Path] = {}

    for name, rows in table_map.items():
        json_path = final_dir / f"{name}.json"
        csv_path = final_dir / f"{name}.csv"

        json_path.write_bytes(orjson.dumps(rows, option=orjson.OPT_INDENT_2))

        if rows:
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame()
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        log.info(
            "Saved {name}: {n} rows -> {jp} / {cp}",
            name=name,
            n=len(rows),
            jp=json_path,
            cp=csv_path,
        )
        output_paths[name] = json_path

    # ── stations_master.json ──────────────────────────────────────────────────
    master_path = final_dir / "stations_master.json"
    master_data = [
        r.model_dump()
        for r in all_results
        if r.parse_success and r.station_detail is not None
    ]
    master_path.write_bytes(orjson.dumps(master_data, option=orjson.OPT_INDENT_2))
    log.info(
        "Saved stations_master.json: {n} records -> {p}",
        n=len(master_data),
        p=master_path,
    )
    output_paths["stations_master"] = master_path

    return output_paths
