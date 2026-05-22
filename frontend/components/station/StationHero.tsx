"use client";

import { MapPin, Star, Clock, Navigation, Share2, Zap, Shield } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { StationDetail } from "@/types/station";

function getHeroBg(chargerType: string | null) {
  switch (chargerType) {
    case "DC":    return "from-orange-950/60 via-slate-900 to-slate-950";
    case "AC":    return "from-blue-950/60 via-slate-900 to-slate-950";
    case "Mixed": return "from-purple-950/60 via-slate-900 to-slate-950";
    default:      return "from-slate-800/60 via-slate-900 to-slate-950";
  }
}

interface Props { station: StationDetail }

export function StationHero({ station }: Props) {
  const rating   = station.avg_rating ? parseFloat(station.avg_rating) : null;
  const isPublic = station.access_type?.toLowerCase() === "public";
  const is24h    = station.operational_time?.toLowerCase().includes("24") ?? false;

  const mapsUrl = station.navigation_link
    ?? (station.latitude && station.longitude
      ? `https://www.google.com/maps/dir/?api=1&destination=${station.latitude},${station.longitude}`
      : null);

  const locationParts = [
    station.area,
    station.city_name ?? station.city_name_cached,
    station.state_name,
  ].filter(Boolean);

  function handleShare() {
    if (typeof navigator !== "undefined" && navigator.share) {
      navigator.share({
        title: station.station_name ?? "EV Station",
        url:   window.location.href,
      });
    } else {
      navigator.clipboard?.writeText(window.location.href);
    }
  }

  return (
    <div className="rounded-xl overflow-hidden border border-border bg-card">
      {/* Banner */}
      <div className={cn("h-40 bg-gradient-to-br relative overflow-hidden", getHeroBg(station.charger_type))}>
        <div className="absolute inset-0 flex items-center justify-center opacity-[0.04]">
          <Zap className="w-56 h-56" />
        </div>
        <div className="absolute top-4 left-4 flex gap-2">
          <ChargerTypeBadge type={station.charger_type} />
          {station.access_type && (
            <span className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border",
              isPublic
                ? "bg-green-500/10 text-green-400 border-green-500/20"
                : "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
            )}>
              <Shield className="w-3 h-3" />
              {station.access_type}
            </span>
          )}
        </div>
        {station.highest_power_kw && (
          <div className="absolute top-4 right-4 bg-black/60 backdrop-blur text-white text-sm font-bold px-3 py-1 rounded-full">
            ⚡ {parseFloat(station.highest_power_kw)} kW
          </div>
        )}
        {station.is_connected === false && (
          <div className="absolute bottom-4 left-4 bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-medium px-2.5 py-1 rounded-full backdrop-blur">
            Offline
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h1 className="text-xl font-bold leading-tight mb-1.5">
              {station.station_name ?? "Unknown Station"}
            </h1>
            {locationParts.length > 0 && (
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <MapPin className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{locationParts.join(", ")}</span>
              </div>
            )}
            {station.address && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                {station.address}
              </p>
            )}
          </div>

          <div className="flex flex-col items-start sm:items-end gap-1.5 shrink-0">
            <StatusBadge availability={station.availability} />
            {rating != null && (
              <span className="flex items-center gap-1 text-sm">
                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                <span className="font-semibold">{rating.toFixed(1)}</span>
                {station.review_count != null && (
                  <span className="text-muted-foreground text-xs">
                    ({station.review_count.toLocaleString()})
                  </span>
                )}
              </span>
            )}
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground mb-4 pb-4 border-b border-border/50">
          {(station.operator_name ?? station.operator_name_cached) && (
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              {station.operator_name ?? station.operator_name_cached}
            </span>
          )}
          {station.operational_time && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {is24h
                ? <span className="text-green-400 font-medium">Open 24/7</span>
                : station.operational_time}
            </span>
          )}
          <span>
            {station.total_charger_count} charger{station.total_charger_count !== 1 ? "s" : ""}
          </span>
          <span>
            {station.available_connector_count}/{station.total_connector_count} connectors available
          </span>
          {station.ac_charger_count > 0 && (
            <span className="text-blue-400">{station.ac_charger_count} AC</span>
          )}
          {station.dc_charger_count > 0 && (
            <span className="text-orange-400">{station.dc_charger_count} DC</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {mapsUrl && (
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 h-9 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
            >
              <Navigation className="w-3.5 h-3.5" />
              Navigate
            </a>
          )}
          <button
            onClick={handleShare}
            className="inline-flex items-center gap-1.5 px-4 h-9 border border-border text-sm text-muted-foreground rounded-lg hover:bg-accent hover:text-foreground transition-colors"
          >
            <Share2 className="w-3.5 h-3.5" />
            Share
          </button>
        </div>
      </div>
    </div>
  );
}
