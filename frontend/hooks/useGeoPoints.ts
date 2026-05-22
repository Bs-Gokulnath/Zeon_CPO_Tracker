import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { MapPoint } from "@/types/station";
import type { StationFilters } from "@/types/filters";

export function useGeoPoints(filters?: StationFilters) {
  // /stations/geo ignores pagination + sort, so strip them out of the query key + params
  const { page: _p, page_size: _ps, sort_by: _s, ...geoFilters } = filters ?? {};
  return useQuery({
    queryKey: ["stations", "geo", geoFilters],
    queryFn:  () => apiFetch<MapPoint[]>("/stations/geo", geoFilters as Record<string, unknown>),
    staleTime: 5 * 60 * 1000,
  });
}
