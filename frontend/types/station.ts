export interface StationAggStats {
  total_stations:     number;
  available_stations: number;
  total_chargers:     number;
  total_connectors:   number;
  cities_covered:     number;
  operators_count:    number;
}

export interface StationSummary {
  id:                        number;
  station_name:              string | null;
  city_name_cached:          string | null;
  operator_name_cached:      string | null;
  latitude:                  string | null;
  longitude:                 string | null;
  availability:              string | null;
  charger_type:              string | null;
  highest_power_kw:          string | null;
  total_charger_count:       number;
  available_connector_count: number;
  avg_rating:                string | null;
  review_count:              number | null;
  access_type:               string | null;
  min_ac_price:              string | null;
  min_dc_price:              string | null;
  has_amenities:             boolean;
  scraped_at:                string | null;
}

export interface ConnectorOut {
  id:               number;
  display_id:       number | null;
  connector_type:   string | null;
  connector_type_id: number | null;
  availability:     boolean | null;
  connector_status: string | null;
  error_message:    string | null;
  connector_image:  string | null;
}

export interface ChargerOut {
  id:                        number;
  charger_name:              string | null;
  type:                      string | null;
  power_rating_kw:           string | null;
  price:                     string | null;
  currency:                  string | null;
  price_display:             string | null;
  connector_count:           number;
  available_connector_count: number;
  connectors:                ConnectorOut[];
}

export interface AmenityOut {
  id:   number;
  type: string;
  icon: string | null;
}

export interface NearbyStationOut {
  nearby_station_id: number;
  station_name:      string | null;
  latitude:          string | null;
  longitude:         string | null;
  access_type:       number | null;
  avg_review_rating: string | null;
  is_connected:      boolean | null;
  station_types:     string | null;
  branding_logo:     string | null;
}

export interface ReviewSummaryOut {
  avg_rating:      string | null;
  review_count:    number;
  rating_1_count:  number;
  rating_2_count:  number;
  rating_3_count:  number;
  rating_4_count:  number;
  rating_5_count:  number;
}

export interface StationDetail {
  id:                        number;
  station_name:              string | null;
  city_name:                 string | null;
  state_name:                string | null;
  operator_name:             string | null;
  city_name_cached:          string | null;
  operator_name_cached:      string | null;
  address:                   string | null;
  area:                      string | null;
  landmark:                  string | null;
  latitude:                  string | null;
  longitude:                 string | null;
  access_type:               string | null;
  availability:              string | null;
  is_connected:              boolean | null;
  operational_time:          string | null;
  charger_type:              string | null;
  highest_power_kw:          string | null;
  ac_charger_count:          number;
  dc_charger_count:          number;
  total_charger_count:       number;
  total_connector_count:     number;
  available_connector_count: number;
  min_ac_price:              string | null;
  max_ac_price:              string | null;
  min_dc_price:              string | null;
  max_dc_price:              string | null;
  avg_rating:                string | null;
  review_count:              number | null;
  has_amenities:             boolean;
  station_image_url:         string | null;
  station_banner:            string | null;
  navigation_link:           string | null;
  scraped_at:                string | null;
  run_id:                    string | null;
  chargers:                  ChargerOut[];
  amenities:                 AmenityOut[];
  nearby_stations:           NearbyStationOut[];
  review_summary:            ReviewSummaryOut | null;
}

export interface MapPoint {
  id:           number;
  latitude:     string | null;
  longitude:    string | null;
  availability: string | null;
  charger_type: string | null;
}

export interface SearchHit {
  id:           number;
  station_name: string | null;
  city_name:    string | null;
  state_name:   string | null;
  charger_type: string | null;
  availability: string | null;
}

export interface NearbyResult {
  id:                        number;
  station_name:              string | null;
  latitude:                  string | null;
  longitude:                 string | null;
  distance_km:               number;
  availability:              string | null;
  charger_type:              string | null;
  highest_power_kw:          string | null;
  available_connector_count: number;
  avg_rating:                string | null;
  access_type:               string | null;
}
