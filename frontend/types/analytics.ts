export interface OverviewStats {
  total_stations:   number;
  available_stations: number;
  total_chargers:   number;
  total_connectors: number;
  ac_stations:      number;
  dc_stations:      number;
  mixed_stations:   number;
  avg_rating:       number | null;
  states_covered:   number;
  cities_covered:   number;
  operators_count:  number;
}

export interface StateDistributionItem {
  state_id:          number;
  state_name:        string;
  total_stations:    number;
  available_stations: number;
  dc_stations:       number;
  ac_stations:       number;
  mixed_stations:    number;
  total_chargers:    number;
  avg_rating:        number | null;
}

export interface OperatorDistributionItem {
  operator_id:       number;
  operator_name:     string;
  operator_type:     string | null;
  total_stations:    number;
  available_stations: number;
  dc_stations:       number;
  ac_stations:       number;
  total_chargers:    number;
  avg_rating:        number | null;
}

export interface ChargerSpeedItem {
  speed_category:  string;
  charger_type:    string;
  charger_count:   number;
  avg_price:       number | null;
  min_power_kw:    number | null;
  max_power_kw:    number | null;
}

export interface AcDcBreakdown {
  ac_stations:          number;
  dc_stations:          number;
  mixed_stations:       number;
  total_ac_chargers:    number;
  total_dc_chargers:    number;
  avg_min_ac_price:     number | null;
  avg_min_dc_price:     number | null;
  avg_highest_power_kw: number | null;
}
