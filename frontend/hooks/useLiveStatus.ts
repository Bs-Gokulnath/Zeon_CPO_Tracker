import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { LiveStatus } from "@/types/station";

export function useLiveStatus(stationId: number) {
  return useQuery<LiveStatus>({
    queryKey:  ["station", stationId, "live"],
    queryFn:   () => apiFetch<LiveStatus>(`/stations/${stationId}/live`),
    staleTime: 30_000,   // re-fetch after 30s (matches backend cache TTL)
    retry:     1,
  });
}
