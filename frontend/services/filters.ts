import { apiFetch } from "@/lib/api-client";
import type { FiltersResponse } from "@/types/filters";

export const filtersApi = {
  get: () => apiFetch<FiltersResponse>("/filters"),
};
