import { MapPin, Zap, Plug, Building2, Network } from "lucide-react";
import { KPICard } from "./KPICard";
import type { StationAggStats } from "@/types/station";

interface KPIRowProps {
  stats:    StationAggStats | null | undefined;
  loading?: boolean;
}

export function KPIRow({ stats, loading }: KPIRowProps) {
  const cards = [
    {
      label:     "Total Stations",
      value:     stats?.total_stations ?? 0,
      icon:      MapPin,
      iconColor: "bg-primary/10 text-primary",
      subtext:   stats ? `${(stats.available_stations ?? 0).toLocaleString()} available` : undefined,
    },
    {
      label:     "Total Chargers",
      value:     stats?.total_chargers ?? 0,
      icon:      Zap,
      iconColor: "bg-orange-500/10 text-orange-400",
    },
    {
      label:     "Connectors",
      value:     stats?.total_connectors ?? 0,
      icon:      Plug,
      iconColor: "bg-blue-500/10 text-blue-400",
    },
    {
      label:     "Cities",
      value:     stats?.cities_covered ?? 0,
      icon:      Building2,
      iconColor: "bg-purple-500/10 text-purple-400",
    },
    {
      label:     "Operators",
      value:     stats?.operators_count ?? 0,
      icon:      Network,
      iconColor: "bg-cyan-500/10 text-cyan-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 p-4">
      {cards.map((c) => (
        <KPICard key={c.label} {...c} loading={loading} />
      ))}
    </div>
  );
}
