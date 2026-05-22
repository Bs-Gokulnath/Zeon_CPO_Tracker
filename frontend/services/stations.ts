import { apiFetch } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { StationDetail, StationSummary, NearbyResult, SearchHit } from "@/types/station";
import type { StationFilters } from "@/types/filters";

export const stationsApi = {
  list: (filters: StationFilters) =>
    apiFetch<PaginatedResponse<StationSummary>>("/stations", filters as Record<string, unknown>),

  getById: (id: number) =>
    apiFetch<StationDetail>(`/stations/${id}`),

  nearby: (lat: number, lon: number, radius_km: number, charger_type?: string, limit = 20) =>
    apiFetch<NearbyResult[]>("/nearby", { lat, lon, radius_km, charger_type, limit }),

  search: (q: string, limit = 10) =>
    apiFetch<SearchHit[]>("/search", { q, limit }),

  autocomplete: (q: string, limit = 10) =>
    apiFetch<SearchHit[]>("/search/autocomplete", { q, limit }),
};
