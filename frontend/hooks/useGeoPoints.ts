import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { MapPoint } from "@/types/station";

export function useGeoPoints() {
  return useQuery({
    queryKey: ["stations", "geo"],
    queryFn:  () => apiFetch<MapPoint[]>("/stations/geo"),
    staleTime: 5 * 60 * 1000,
  });
}
