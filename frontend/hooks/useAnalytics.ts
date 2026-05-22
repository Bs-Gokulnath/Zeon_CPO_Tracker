import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/services/analytics";

export function useOverview(filters?: Record<string, unknown>) {
  const hasFilters = filters != null && Object.keys(filters).length > 0;
  return useQuery({
    queryKey: ["analytics", "overview", hasFilters ? filters : null],
    queryFn:  () => analyticsApi.overview(hasFilters ? filters : undefined),
    staleTime: hasFilters ? 30_000 : 5 * 60 * 1000,
  });
}

export function useStateDistribution() {
  return useQuery({
    queryKey: ["analytics", "state-distribution"],
    queryFn:  analyticsApi.stateDistribution,
    staleTime: 5 * 60 * 1000,
  });
}

export function useOperatorDistribution() {
  return useQuery({
    queryKey: ["analytics", "operator-distribution"],
    queryFn:  analyticsApi.operatorDistribution,
    staleTime: 5 * 60 * 1000,
  });
}

export function useChargerSpeed() {
  return useQuery({
    queryKey: ["analytics", "charger-speed"],
    queryFn:  analyticsApi.chargerSpeed,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAcDcBreakdown() {
  return useQuery({
    queryKey: ["analytics", "ac-dc-breakdown"],
    queryFn:  analyticsApi.acDcBreakdown,
    staleTime: 5 * 60 * 1000,
  });
}
