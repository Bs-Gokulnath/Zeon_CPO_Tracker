import { useQuery } from "@tanstack/react-query";
import { stationsApi } from "@/services/stations";

export function useStation(id: number | null) {
  return useQuery({
    queryKey:  ["station", id],
    queryFn:   () => stationsApi.getById(id!),
    enabled:   id != null,
    staleTime: 5 * 60 * 1000,
  });
}
