export type SortBy =
  | "rating" | "power" | "price_asc" | "price_desc"
  | "connector_count" | "charger_count" | "name" | "id";

export interface StationFilters {
  state_id?:          number[];
  city_id?:           number[];
  operator_id?:       number[];
  charger_type?:      string[];
  access_type?:       string[];
  connector_type_id?: number;
  availability?:      "Available";
  min_kw?:            number;
  max_kw?:            number;
  min_price?:         number;
  max_price?:         number;
  min_rating?:        number;
  has_amenities?:     boolean;
  q?:                 string;
  sort_by?:           SortBy;
  page?:              number;
  page_size?:         number;
}

export interface StateItem   { id: number; name: string; code: string | null }
export interface CityItem    { id: number; name: string; state_id: number }
export interface OperatorItem { id: number; name: string; operator_type: string | null }
export interface ConnectorTypeItem { id: number; name: string | null }

export interface FiltersResponse {
  states:          StateItem[];
  cities:          CityItem[];
  operators:       OperatorItem[];
  charger_types:   string[];
  connector_types: ConnectorTypeItem[];
  access_types:    string[];
  price_range:     { min: number; max: number };
  rating_buckets:  { label: string; min: number | null; max: number | null }[];
}
