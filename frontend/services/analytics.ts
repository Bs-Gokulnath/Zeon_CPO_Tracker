import { apiFetch } from "@/lib/api-client";
import type {
  OverviewStats, StateDistributionItem, OperatorDistributionItem,
  ChargerSpeedItem, AcDcBreakdown
} from "@/types/analytics";

export const analyticsApi = {
  overview: (filters?: Record<string, unknown>) =>
    apiFetch<OverviewStats>("/analytics/overview", filters),
  stateDistribution:    () => apiFetch<StateDistributionItem[]>("/analytics/state-distribution"),
  operatorDistribution: () => apiFetch<OperatorDistributionItem[]>("/analytics/operator-distribution"),
  chargerSpeed:         () => apiFetch<ChargerSpeedItem[]>("/analytics/charger-speed"),
  acDcBreakdown:        () => apiFetch<AcDcBreakdown>("/analytics/ac-dc-breakdown"),
};
