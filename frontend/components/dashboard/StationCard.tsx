"use client";

import { memo } from "react";
import Link from "next/link";
import { Star, Zap, Plug, ChevronRight, MapPin } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { StationSummary } from "@/types/station";

interface StationCardProps {
  station: StationSummary;
}

function getBgGradient(type: string | null) {
  switch (type) {
    case "DC":    return "from-orange-950/40 to-slate-900/80";
    case "AC":    return "from-blue-950/40 to-slate-900/80";
    case "Mixed": return "from-purple-950/40 to-slate-900/80";
    default:      return "from-slate-800/40 to-slate-900/80";
  }
}

export const StationCard = memo(function StationCard({ station }: StationCardProps) {
  const price  = station.min_dc_price ?? station.min_ac_price;
  const rating = station.avg_rating ? parseFloat(station.avg_rating) : null;

  return (
    <Link href={`/station/${station.id}`}>
      <div className="group relative bg-card border border-border rounded-xl p-4 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 transition-all duration-200 cursor-pointer">
        {/* Image placeholder with gradient */}
        <div className={cn(
          "h-[90px] rounded-lg mb-3 bg-gradient-to-br relative overflow-hidden",
          getBgGradient(station.charger_type)
        )}>
          <div className="absolute inset-0 flex items-center justify-center opacity-20">
            <Zap className="w-10 h-10" />
          </div>
          {station.highest_power_kw && (
            <div className="absolute top-2 right-2 bg-black/60 backdrop-blur text-white text-xs font-bold px-2 py-0.5 rounded-full">
              ⚡ {parseFloat(station.highest_power_kw)} kW
            </div>
          )}
          <div className="absolute bottom-2 left-2">
            <ChargerTypeBadge type={station.charger_type} />
          </div>
        </div>

        <h3 className="font-medium text-sm leading-snug line-clamp-1 group-hover:text-primary transition-colors mb-1">
          {station.station_name ?? "Unknown Station"}
        </h3>

        <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
          <MapPin className="w-3 h-3 shrink-0" />
          <span className="truncate">{station.city_name_cached ?? "—"}</span>
          {station.operator_name_cached && (
            <span className="text-muted-foreground/50">· {station.operator_name_cached}</span>
          )}
        </div>

        <div className="flex items-center justify-between mb-3">
          <StatusBadge availability={station.availability} />
          {rating != null ? (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
              <span className="font-medium text-foreground">{rating.toFixed(1)}</span>
              {station.review_count && <span>({station.review_count})</span>}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">No ratings</span>
          )}
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-border/50 pt-2.5">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {station.total_charger_count} charger{station.total_charger_count !== 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            <Plug className="w-3 h-3" />
            {station.available_connector_count}/{station.total_charger_count * 2}
          </span>
          <span className="font-medium text-foreground">
            {price ? `₹${parseFloat(price).toFixed(0)}/kWh` : "—"}
          </span>
        </div>

        <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/30 group-hover:text-primary/50 transition-colors" />
      </div>
    </Link>
  );
});
