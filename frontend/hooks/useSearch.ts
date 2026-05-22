import { useQuery } from "@tanstack/react-query";
import { stationsApi } from "@/services/stations";

export function useSearch(q: string, limit = 10) {
  return useQuery({
    queryKey: ["search", q, limit],
    queryFn:  () => stationsApi.search(q, limit),
    enabled:  q.length >= 1,
    staleTime: 30 * 1000,
  });
}

export function useAutocomplete(q: string) {
  return useQuery({
    queryKey: ["autocomplete", q],
    queryFn:  () => stationsApi.autocomplete(q, 8),
    enabled:  q.length >= 1,
    staleTime: 30 * 1000,
  });
}
