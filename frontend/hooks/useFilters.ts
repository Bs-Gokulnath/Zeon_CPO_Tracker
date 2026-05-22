import { useQuery } from "@tanstack/react-query";
import { filtersApi } from "@/services/filters";

export function useFilters() {
  return useQuery({
    queryKey:  ["filters"],
    queryFn:   filtersApi.get,
    staleTime: 30 * 60 * 1000,  // 30 min — near static
    gcTime:    60 * 60 * 1000,
  });
}
