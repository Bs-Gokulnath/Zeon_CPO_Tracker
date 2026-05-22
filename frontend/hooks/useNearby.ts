import { useQuery } from "@tanstack/react-query";
import { stationsApi } from "@/services/stations";

export function useNearby(
  lat: number | null,
  lon: number | null,
  radius_km = 5,
  charger_type?: string
) {
  return useQuery({
    queryKey: ["nearby", lat, lon, radius_km, charger_type],
    queryFn:  () => stationsApi.nearby(lat!, lon!, radius_km, charger_type),
    enabled:  lat != null && lon != null,
    staleTime: 2 * 60 * 1000,
  });
}
