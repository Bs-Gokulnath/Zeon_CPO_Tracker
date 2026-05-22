"use client";

import { useMemo } from "react";
import {
  parseAsFloat,
  parseAsInteger,
  parseAsString,
  useQueryStates,
} from "nuqs";
import type { StationFilters, SortBy } from "@/types/filters";

const PAGE_SIZE = 12;

const parsers = {
  state_id:          parseAsInteger,
  city_id:           parseAsInteger,
  operator_id:       parseAsInteger,
  charger_type:      parseAsString,
  connector_type_id: parseAsInteger,
  access_type:       parseAsString,
  availability:      parseAsString,
  min_kw:            parseAsFloat,
  max_kw:            parseAsFloat,
  min_price:         parseAsFloat,
  max_price:         parseAsFloat,
  min_rating:        parseAsFloat,
  q:                 parseAsString,
  sort_by:           parseAsString.withDefault("rating"),
  page:              parseAsInteger.withDefault(1),
};

export function useFiltersParams() {
  const [params, setParams] = useQueryStates(parsers, { history: "push" });

  const filters = useMemo<StationFilters>(() => {
    const f: StationFilters = {
      sort_by:   (params.sort_by || "rating") as SortBy,
      page:      params.page,
      page_size: PAGE_SIZE,
    };
    if (params.state_id)           f.state_id          = params.state_id;
    if (params.city_id)            f.city_id           = params.city_id;
    if (params.operator_id)        f.operator_id       = params.operator_id;
    if (params.charger_type)       f.charger_type      = params.charger_type as StationFilters["charger_type"];
    if (params.connector_type_id)  f.connector_type_id = params.connector_type_id;
    if (params.access_type)        f.access_type       = params.access_type as StationFilters["access_type"];
    if (params.availability)       f.availability      = params.availability as "Available";
    if (params.min_kw != null)     f.min_kw            = params.min_kw;
    if (params.max_kw != null)     f.max_kw            = params.max_kw;
    if (params.min_price != null)  f.min_price         = params.min_price;
    if (params.max_price != null)  f.max_price         = params.max_price;
    if (params.min_rating != null) f.min_rating        = params.min_rating;
    if (params.q)                  f.q                 = params.q;
    return f;
  }, [params]);

  const setFilter = (updates: Partial<typeof params>) =>
    setParams({ ...updates, page: 1 });

  const setPage   = (p: number) => setParams({ page: p });
  const setSortBy = (s: string) => setFilter({ sort_by: s });

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (params.state_id)           n++;
    if (params.city_id)            n++;
    if (params.operator_id)        n++;
    if (params.charger_type)       n++;
    if (params.connector_type_id)  n++;
    if (params.access_type)        n++;
    if (params.availability)       n++;
    if (params.min_kw != null)     n++;
    if (params.max_kw != null)     n++;
    if (params.min_price != null)  n++;
    if (params.max_price != null)  n++;
    if (params.min_rating != null) n++;
    return n;
  }, [params]);

  const clearFilters = () =>
    setParams({
      state_id: null, city_id: null, operator_id: null,
      charger_type: null, connector_type_id: null,
      access_type: null, availability: null,
      min_kw: null, max_kw: null,
      min_price: null, max_price: null,
      min_rating: null, q: null,
      page: 1,
    });

  return {
    params,
    setParams,
    setFilter,
    filters,
    setPage,
    setSortBy,
    activeFilterCount,
    clearFilters,
  };
}
