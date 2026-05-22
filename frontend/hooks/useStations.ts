import { useQuery } from "@tanstack/react-query";
import { stationsApi } from "@/services/stations";
import type { StationFilters } from "@/types/filters";

export function useStations(filters: StationFilters) {
  return useQuery({
    queryKey: ["stations", filters],
    queryFn:  () => stationsApi.list(filters),
    staleTime: 2 * 60 * 1000,
    placeholderData: (prev) => prev,  // keep old data while loading
  });
}
