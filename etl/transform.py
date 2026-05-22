from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from typing import NamedTuple

import pandas as pd

from etl.extract import ExtractResult
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("etl.transform")


# ── Operator normalization rules ──────────────────────────────────────────────

class _Rule(NamedTuple):
    pattern: str
    normalized_name: str
    operator_type: str


# Ordered by specificity — first match wins
OPERATOR_RULES: list[_Rule] = [
    # EV Networks
    _Rule(r"(?i)^statiq\b",                      "Statiq",           "EV_NETWORK"),
    _Rule(r"(?i)^tata\s*power\b",                "TATA Power",       "EV_NETWORK"),
    _Rule(r"(?i)^chargezone\b",                  "ChargeZone",       "EV_NETWORK"),
    _Rule(r"(?i)^eesl\b",                        "EESL",             "EV_NETWORK"),
    _Rule(r"(?i)^fortum\b",                      "Fortum",           "EV_NETWORK"),
    _Rule(r"(?i)^sunfuel\b",                     "Sunfuel",          "EV_NETWORK"),
    _Rule(r"(?i)^ather\b",                       "Ather",            "EV_NETWORK"),
    _Rule(r"(?i)^zeon\b",                        "Zeon",             "EV_NETWORK"),
    _Rule(r"(?i)^adani\b",                       "Adani",            "EV_NETWORK"),
    _Rule(r"(?i)^glida\b",                       "Glida",            "EV_NETWORK"),
    _Rule(r"(?i)^kazam\b",                       "Kazam",            "EV_NETWORK"),
    _Rule(r"(?i)^volttic\b",                     "Volttic",          "EV_NETWORK"),
    _Rule(r"(?i)^revolt\b",                      "Revolt",           "EV_NETWORK"),
    _Rule(r"(?i)^okaya\b",                       "Okaya",            "EV_NETWORK"),
    _Rule(r"(?i)^ampere\b",                      "Ampere",           "EV_NETWORK"),
    _Rule(r"(?i)^delta\b",                       "Delta",            "EV_NETWORK"),
    _Rule(r"(?i)^mass.?tech\b",                  "MassTech",         "EV_NETWORK"),
    _Rule(r"(?i)^jio.?bp\b",                     "JIO-BP",           "EV_NETWORK"),
    _Rule(r"(?i)^charge\s*point\b",              "ChargePoint",      "EV_NETWORK"),
    # Fuel Retail
    _Rule(r"(?i)^bpcl\b|bharat\s*petroleum",     "BPCL",             "FUEL_RETAIL"),
    _Rule(r"(?i)^iocl\b|indian\s*oil",           "IOCL",             "FUEL_RETAIL"),
    _Rule(r"(?i)^hpcl\b|hindustan\s*petroleum",  "HPCL",             "FUEL_RETAIL"),
    _Rule(r"(?i)^reliance\s*(?:bp|petro)",       "Reliance",         "FUEL_RETAIL"),
    _Rule(r"(?i)petrol\s*pump|fuel\s*station",   "Petrol Pump",      "FUEL_RETAIL"),
    # Hospitality
    _Rule(r"(?i)^itc\b",                         "ITC",              "HOSPITALITY"),
    _Rule(r"(?i)^marriott\b",                    "Marriott",         "HOSPITALITY"),
    _Rule(r"(?i)^hilton\b",                      "Hilton",           "HOSPITALITY"),
    _Rule(r"(?i)^hyatt\b",                       "Hyatt",            "HOSPITALITY"),
    _Rule(r"(?i)^oberoi\b",                      "Oberoi",           "HOSPITALITY"),
    _Rule(r"(?i)^taj\b",                         "Taj",              "HOSPITALITY"),
    _Rule(r"(?i)^oyo\b",                         "OYO",              "HOSPITALITY"),
    _Rule(r"(?i)^lemon\s*tree\b",                "Lemon Tree",       "HOSPITALITY"),
    _Rule(r"(?i)\b(?:hotel|resort|lodge|inn)\b", "Hotel",            "HOSPITALITY"),
    # Utilities
    _Rule(r"(?i)^bescom\b",                      "BESCOM",           "UTILITY"),
    _Rule(r"(?i)^msedcl\b",                      "MSEDCL",           "UTILITY"),
    _Rule(r"(?i)^torrent\b",                     "Torrent",          "UTILITY"),
    _Rule(r"(?i)^tneb\b",                        "TNEB",             "UTILITY"),
    _Rule(r"(?i)^kseb\b",                        "KSEB",             "UTILITY"),
    _Rule(r"(?i)^apepdcl\b|^apspdcl\b",          "APEPDCL",          "UTILITY"),
    # Automotive
    _Rule(r"(?i)^mg\b|morris\s*garages",         "MG",               "AUTOMOTIVE"),
    _Rule(r"(?i)^hyundai\b",                     "Hyundai",          "AUTOMOTIVE"),
    _Rule(r"(?i)^kia\b",                         "KIA",              "AUTOMOTIVE"),
    _Rule(r"(?i)^bmw\b",                         "BMW",              "AUTOMOTIVE"),
    _Rule(r"(?i)^audi\b",                        "Audi",             "AUTOMOTIVE"),
    _Rule(r"(?i)^mercedes\b",                    "Mercedes",         "AUTOMOTIVE"),
    _Rule(r"(?i)^volkswagen\b|^vw\b",            "Volkswagen",       "AUTOMOTIVE"),
    _Rule(r"(?i)^volvo\b",                       "Volvo",            "AUTOMOTIVE"),
    _Rule(r"(?i)^tata\b",                        "TATA",             "AUTOMOTIVE"),
]

# Compile patterns once at module load
_COMPILED_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r.pattern), r.normalized_name, r.operator_type)
    for r in OPERATOR_RULES
]


def normalize_operator(station_name: str | None) -> tuple[str, str]:
    """Return (normalized_name, operator_type) for a station name."""
    if not station_name:
        return "Unknown", "OTHER"
    for pattern, name, op_type in _COMPILED_RULES:
        if pattern.search(station_name):
            return name, op_type
    return "Unknown", "OTHER"


# ── City → State mapping ──────────────────────────────────────────────────────

# Canonical Indian state/UT names — used for address-based fallback resolution
INDIAN_STATES: list[str] = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Delhi", "Chandigarh", "Jammu & Kashmir", "Ladakh",
    "Puducherry", "Andaman & Nicobar Islands",
    "Dadra & Nagar Haveli and Daman & Diu",
]
# Pre-lowercased for O(1) comparisons at call time
_STATES_LOWER: list[tuple[str, str]] = [(s.lower(), s) for s in INDIAN_STATES]

CITY_TO_STATE: dict[str, str] = {
    # Delhi NCR
    "Delhi": "Delhi", "New Delhi": "Delhi", "South Delhi": "Delhi",
    "North Delhi": "Delhi", "East Delhi": "Delhi", "West Delhi": "Delhi",
    "Central Delhi": "Delhi",
    "Noida": "Uttar Pradesh", "Greater Noida": "Uttar Pradesh",
    "Ghaziabad": "Uttar Pradesh", "Surajpur": "Uttar Pradesh",
    "Gurugram": "Haryana", "Gurgaon": "Haryana",
    "Faridabad": "Haryana", "Manesar": "Haryana", "Bahadurgarh": "Haryana",
    # Karnataka
    "Bengaluru": "Karnataka", "Bangalore": "Karnataka",
    "Mysuru": "Karnataka", "Mysore": "Karnataka",
    "Mangaluru": "Karnataka", "Mangalore": "Karnataka",
    "Hubli": "Karnataka", "Dharwad": "Karnataka",
    "Belagavi": "Karnataka", "Belgaum": "Karnataka",
    "Udupi": "Karnataka", "Hassan": "Karnataka", "Shimoga": "Karnataka",
    "Shivamogga": "Karnataka", "Davanagere": "Karnataka", "Tumkur": "Karnataka",
    "Mandya": "Karnataka", "Kolar": "Karnataka", "Kalaburagi": "Karnataka",
    "Ballari": "Karnataka", "Vijayapura": "Karnataka", "Bidar": "Karnataka",
    "Raichur": "Karnataka", "Chitradurga": "Karnataka", "Bagalkot": "Karnataka",
    "Chikkamagaluru": "Karnataka", "Kodagu": "Karnataka", "Coorg": "Karnataka",
    # Maharashtra
    "Mumbai": "Maharashtra", "Navi Mumbai": "Maharashtra", "Thane": "Maharashtra",
    "Kalyan": "Maharashtra", "Dombivli": "Maharashtra", "Ulhasnagar": "Maharashtra",
    "Pune": "Maharashtra", "Pimpri-Chinchwad": "Maharashtra", "Nashik": "Maharashtra",
    "Nagpur": "Maharashtra", "Aurangabad": "Maharashtra", "Solapur": "Maharashtra",
    "Kolhapur": "Maharashtra", "Amravati": "Maharashtra", "Satara": "Maharashtra",
    "Latur": "Maharashtra", "Ratnagiri": "Maharashtra", "Sangli": "Maharashtra",
    "Ahmednagar": "Maharashtra", "Dhule": "Maharashtra", "Jalgaon": "Maharashtra",
    "Nanded": "Maharashtra", "Akola": "Maharashtra", "Chandrapur": "Maharashtra",
    "Palghar": "Maharashtra", "Lonavala": "Maharashtra", "Shirdi": "Maharashtra",
    # Tamil Nadu
    "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu", "Madurai": "Tamil Nadu",
    "Tiruchirappalli": "Tamil Nadu", "Trichy": "Tamil Nadu", "Salem": "Tamil Nadu",
    "Tirunelveli": "Tamil Nadu", "Vellore": "Tamil Nadu", "Erode": "Tamil Nadu",
    "Tiruppur": "Tamil Nadu", "Thanjavur": "Tamil Nadu", "Dindigul": "Tamil Nadu",
    "Hosur": "Tamil Nadu", "Ooty": "Tamil Nadu", "Nagercoil": "Tamil Nadu",
    "Thoothukudi": "Tamil Nadu", "Tuticorin": "Tamil Nadu", "Kanchipuram": "Tamil Nadu",
    "Krishnagiri": "Tamil Nadu", "Dharmapuri": "Tamil Nadu", "Namakkal": "Tamil Nadu",
    "Karur": "Tamil Nadu", "Cuddalore": "Tamil Nadu",
    # Telangana
    "Hyderabad": "Telangana", "Secunderabad": "Telangana", "Warangal": "Telangana",
    "Karimnagar": "Telangana", "Nizamabad": "Telangana", "Khammam": "Telangana",
    "Ramagundam": "Telangana", "Nalgonda": "Telangana", "Sangareddy": "Telangana",
    "Mahabubnagar": "Telangana", "Medak": "Telangana",
    # Andhra Pradesh
    "Vijayawada": "Andhra Pradesh", "Visakhapatnam": "Andhra Pradesh",
    "Vizag": "Andhra Pradesh", "Guntur": "Andhra Pradesh", "Nellore": "Andhra Pradesh",
    "Kurnool": "Andhra Pradesh", "Tirupati": "Andhra Pradesh",
    "Rajahmundry": "Andhra Pradesh", "Rajamahendravaram": "Andhra Pradesh",
    "Kakinada": "Andhra Pradesh", "Eluru": "Andhra Pradesh", "Ongole": "Andhra Pradesh",
    "Anantapur": "Andhra Pradesh", "Kadapa": "Andhra Pradesh", "Chittoor": "Andhra Pradesh",
    # Gujarat
    "Ahmedabad": "Gujarat", "Surat": "Gujarat", "Vadodara": "Gujarat",
    "Rajkot": "Gujarat", "Bhavnagar": "Gujarat", "Jamnagar": "Gujarat",
    "Gandhinagar": "Gujarat", "Junagadh": "Gujarat", "Anand": "Gujarat",
    "Bharuch": "Gujarat", "Nadiad": "Gujarat", "Morbi": "Gujarat",
    "Mehsana": "Gujarat", "Surendranagar": "Gujarat", "Porbandar": "Gujarat",
    "Navsari": "Gujarat", "Vapi": "Gujarat",
    # Rajasthan
    "Jaipur": "Rajasthan", "Jodhpur": "Rajasthan", "Udaipur": "Rajasthan",
    "Kota": "Rajasthan", "Ajmer": "Rajasthan", "Bikaner": "Rajasthan",
    "Alwar": "Rajasthan", "Bharatpur": "Rajasthan", "Sikar": "Rajasthan",
    "Bhilwara": "Rajasthan", "Barmer": "Rajasthan", "Jaisalmer": "Rajasthan",
    "Chittorgarh": "Rajasthan", "Neemrana": "Rajasthan", "Bhiwadi": "Rajasthan",
    "Nagaur": "Rajasthan", "Sri Ganganagar": "Rajasthan", "Hanumangarh": "Rajasthan",
    # Uttar Pradesh
    "Lucknow": "Uttar Pradesh", "Kanpur": "Uttar Pradesh", "Agra": "Uttar Pradesh",
    "Varanasi": "Uttar Pradesh", "Meerut": "Uttar Pradesh", "Allahabad": "Uttar Pradesh",
    "Prayagraj": "Uttar Pradesh", "Bareilly": "Uttar Pradesh", "Moradabad": "Uttar Pradesh",
    "Aligarh": "Uttar Pradesh", "Gorakhpur": "Uttar Pradesh", "Saharanpur": "Uttar Pradesh",
    "Jhansi": "Uttar Pradesh", "Mathura": "Uttar Pradesh", "Vrindavan": "Uttar Pradesh",
    "Muzaffarnagar": "Uttar Pradesh", "Firozabad": "Uttar Pradesh",
    "Bulandshahr": "Uttar Pradesh", "Etawah": "Uttar Pradesh",
    # Haryana
    "Rohtak": "Haryana", "Ambala": "Haryana", "Panipat": "Haryana",
    "Sonipat": "Haryana", "Hisar": "Haryana", "Karnal": "Haryana",
    "Yamunanagar": "Haryana", "Bhiwani": "Haryana", "Panchkula": "Haryana",
    "Rewari": "Haryana", "Palwal": "Haryana", "Jind": "Haryana",
    "Kaithal": "Haryana", "Kurukshetra": "Haryana", "Sirsa": "Haryana",
    # Punjab
    "Amritsar": "Punjab", "Ludhiana": "Punjab", "Jalandhar": "Punjab",
    "Patiala": "Punjab", "Bathinda": "Punjab", "Mohali": "Punjab",
    "SAS Nagar": "Punjab", "Pathankot": "Punjab", "Hoshiarpur": "Punjab",
    "Ropar": "Punjab", "Moga": "Punjab", "Firozpur": "Punjab",
    "Sangrur": "Punjab", "Gurdaspur": "Punjab", "Kapurthala": "Punjab",
    # West Bengal
    "Kolkata": "West Bengal", "Howrah": "West Bengal", "Durgapur": "West Bengal",
    "Asansol": "West Bengal", "Siliguri": "West Bengal", "Bardhaman": "West Bengal",
    "Malda": "West Bengal", "Jalpaiguri": "West Bengal", "Kharagpur": "West Bengal",
    "Haldia": "West Bengal",
    # Madhya Pradesh
    "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh", "Jabalpur": "Madhya Pradesh",
    "Gwalior": "Madhya Pradesh", "Ujjain": "Madhya Pradesh", "Sagar": "Madhya Pradesh",
    "Rewa": "Madhya Pradesh", "Satna": "Madhya Pradesh", "Dewas": "Madhya Pradesh",
    "Ratlam": "Madhya Pradesh", "Chhindwara": "Madhya Pradesh", "Pithampur": "Madhya Pradesh",
    "Dhar": "Madhya Pradesh", "Mandsaur": "Madhya Pradesh", "Shivpuri": "Madhya Pradesh",
    # Kerala
    "Kochi": "Kerala", "Thiruvananthapuram": "Kerala", "Kozhikode": "Kerala",
    "Calicut": "Kerala", "Kannur": "Kerala", "Kollam": "Kerala",
    "Thrissur": "Kerala", "Alappuzha": "Kerala", "Palakkad": "Kerala",
    "Malappuram": "Kerala", "Kottayam": "Kerala", "Ernakulam": "Kerala",
    "Kasaragod": "Kerala", "Wayanad": "Kerala", "Idukki": "Kerala",
    # Odisha
    "Bhubaneswar": "Odisha", "Cuttack": "Odisha", "Rourkela": "Odisha",
    "Berhampur": "Odisha", "Sambalpur": "Odisha", "Puri": "Odisha",
    "Balasore": "Odisha", "Brahmapur": "Odisha",
    # Bihar
    "Patna": "Bihar", "Gaya": "Bihar", "Bhagalpur": "Bihar",
    "Muzaffarpur": "Bihar", "Darbhanga": "Bihar", "Purnia": "Bihar",
    # Jharkhand
    "Ranchi": "Jharkhand", "Jamshedpur": "Jharkhand", "Dhanbad": "Jharkhand",
    "Bokaro": "Jharkhand", "Hazaribagh": "Jharkhand",
    # Chhattisgarh
    "Raipur": "Chhattisgarh", "Bhilai": "Chhattisgarh", "Bilaspur": "Chhattisgarh",
    "Durg": "Chhattisgarh", "Korba": "Chhattisgarh", "Raigarh": "Chhattisgarh",
    # Uttarakhand
    "Dehradun": "Uttarakhand", "Haridwar": "Uttarakhand", "Rishikesh": "Uttarakhand",
    "Roorkee": "Uttarakhand", "Haldwani": "Uttarakhand", "Nainital": "Uttarakhand",
    "Mussoorie": "Uttarakhand", "Rudrapur": "Uttarakhand",
    # Himachal Pradesh
    "Shimla": "Himachal Pradesh", "Manali": "Himachal Pradesh",
    "Dharamshala": "Himachal Pradesh", "Solan": "Himachal Pradesh",
    "Kullu": "Himachal Pradesh", "Mandi": "Himachal Pradesh", "Baddi": "Himachal Pradesh",
    # Goa
    "Panaji": "Goa", "Margao": "Goa", "Vasco Da Gama": "Goa", "Mapusa": "Goa",
    "Ponda": "Goa", "Goa": "Goa",
    # Jammu & Kashmir / Ladakh
    "Srinagar": "Jammu & Kashmir", "Jammu": "Jammu & Kashmir",
    "Leh": "Ladakh", "Kargil": "Ladakh",
    # Chandigarh
    "Chandigarh": "Chandigarh",
    # Assam
    "Guwahati": "Assam", "Silchar": "Assam", "Dibrugarh": "Assam",
    "Jorhat": "Assam", "Nagaon": "Assam", "Tinsukia": "Assam",
    # Other NE states
    "Shillong": "Meghalaya", "Agartala": "Tripura", "Imphal": "Manipur",
    "Kohima": "Nagaland", "Dimapur": "Nagaland",
    "Aizawl": "Mizoram", "Itanagar": "Arunachal Pradesh",
    "Gangtok": "Sikkim",
    # UTs
    "Puducherry": "Puducherry", "Pondicherry": "Puducherry",
    "Karaikal": "Puducherry", "Port Blair": "Andaman & Nicobar Islands",
    "Daman": "Dadra & Nagar Haveli and Daman & Diu",
    "Silvassa": "Dadra & Nagar Haveli and Daman & Diu",
}


def _resolve_state(city_name: str | None, address: str | None) -> str | None:
    # Pass 1: direct city → state lookup
    if city_name and city_name in CITY_TO_STATE:
        return CITY_TO_STATE[city_name]
    addr_lower = address.lower() if address else ""
    # Pass 2: scan address for known city names
    if addr_lower:
        for city, state in CITY_TO_STATE.items():
            if city.lower() in addr_lower:
                return state
    # Pass 3: match canonical state name directly in address string
    # (catches addresses like "Ranga Reddy district, Telangana, 509228, India")
    if addr_lower:
        for state_lower, state in _STATES_LOWER:
            if state_lower in addr_lower:
                return state
    return None


_ACCESS_MAP: dict = {1: "public", 2: "captive", "1": "public", "2": "captive"}


def _normalize_access_type(v) -> str | None:
    if v is None or (isinstance(v, float) and v != v):
        return None
    return _ACCESS_MAP.get(v, str(v).lower() if v else None)


def _derive_charger_type(row: pd.Series) -> str | None:
    ac = row.get("ac_charger_count", 0) or 0
    dc = row.get("dc_charger_count", 0) or 0
    if ac > 0 and dc > 0:
        return "Mixed"
    if dc > 0:
        return "DC"
    if ac > 0:
        return "AC"
    return row.get("charger_type") or None


def _content_hash(row: pd.Series) -> str:
    fields = "|".join(
        str(row.get(f, ""))
        for f in (
            "availability", "is_connected", "available_connector_count",
            "avg_rating", "review_count", "highest_power_kw", "total_charger_count",
        )
    )
    return hashlib.sha256(fields.encode()).hexdigest()


@dataclass
class TransformResult:
    stations: pd.DataFrame
    chargers: pd.DataFrame
    connectors: pd.DataFrame
    amenities: pd.DataFrame
    nearby_stations: pd.DataFrame
    connector_types: pd.DataFrame
    operators: pd.DataFrame    # unique operators
    states: pd.DataFrame       # unique states
    cities: pd.DataFrame       # unique (city_name, state_name) pairs
    run_id: str
    elapsed_secs: float


def transform(result: ExtractResult) -> TransformResult:
    t0 = time.monotonic()
    stations = result.stations.copy()
    chargers = result.chargers.copy()
    connectors = result.connectors.copy()
    nearby = result.nearby_stations.copy()

    # ── Stations ──────────────────────────────────────────────────────────────
    stations["city_name"] = stations.get("city_name", pd.Series(dtype=str))
    stations["access_type"] = stations["access_type"].apply(_normalize_access_type)

    # Unrated logic
    if "review_count" in stations.columns and "avg_rating" in stations.columns:
        mask_unrated = (stations["review_count"].fillna(0) == 0)
        stations.loc[mask_unrated, "avg_rating"] = None

    # Operator extraction
    op_pairs = stations["station_name"].apply(normalize_operator)
    stations["operator_normalized_name"] = op_pairs.apply(lambda x: x[0])
    stations["operator_type"] = op_pairs.apply(lambda x: x[1])

    # State resolution
    stations["state_name"] = stations.apply(
        lambda r: _resolve_state(r.get("city_name"), r.get("address")),
        axis=1,
    )

    # Derived charger_type (Mixed when both AC and DC present)
    stations["charger_type"] = stations.apply(_derive_charger_type, axis=1)

    # Content hash for incremental detection
    stations["content_hash"] = stations.apply(_content_hash, axis=1)

    # Run ID
    stations["run_id"] = result.run_id

    # ── Nearby stations: normalise access_type and precompute integer encoding ──
    _ACCESS_INT: dict = {"public": 1, "captive": 2}
    if not nearby.empty and "access_type" in nearby.columns:
        nearby["access_type"] = nearby["access_type"].apply(_normalize_access_type)
        nearby["access_type_int"] = nearby["access_type"].map(_ACCESS_INT)

    # ── Build dimension DataFrames ────────────────────────────────────────────

    # States
    state_names = (
        stations["state_name"]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
        .rename("name")
        .to_frame()
    )
    state_names["code"] = None

    # Cities
    cities_df = (
        stations[["city_name", "state_name"]]
        .dropna(subset=["city_name"])
        .drop_duplicates(subset=["city_name", "state_name"])
        .reset_index(drop=True)
    )

    # Operators
    ops_df = (
        stations[["operator_normalized_name", "operator_type"]]
        .drop_duplicates(subset=["operator_normalized_name"])
        .reset_index(drop=True)
        .rename(columns={"operator_normalized_name": "name", "operator_type": "operator_type"})
    )
    ops_df["normalized_name"] = ops_df["name"]
    ops_df["logo_url"] = None

    elapsed = time.monotonic() - t0
    log.info(
        "Transform complete in {t:.2f}s — {s} stations, {op} operators, "
        "{st} states, {ci} cities",
        t=elapsed, s=len(stations), op=len(ops_df),
        st=len(state_names), ci=len(cities_df),
    )

    return TransformResult(
        stations=stations,
        chargers=chargers,
        connectors=connectors,
        amenities=result.amenities,
        nearby_stations=nearby,
        connector_types=result.connector_types,
        operators=ops_df,
        states=state_names,
        cities=cities_df,
        run_id=result.run_id,
        elapsed_secs=elapsed,
    )
