"use client";

import { useState } from "react";
import {
  X, MapPin, Star, Clock, Zap, Copy, Navigation,
  ChevronDown, Shield, Plug, CheckCircle2, XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStation } from "@/hooks/useStation";
import { Skeleton } from "@/components/ui/skeleton";
import type { ChargerOut, ConnectorOut, NearbyStationOut, ReviewSummaryOut } from "@/types/station";

// ── Banner ─────────────────────────────────────────────────────────────────────
function Banner({ chargerType }: { chargerType: string | null }) {
  const grad =
    chargerType === "DC"    ? "from-orange-900 via-slate-900 to-slate-950" :
    chargerType === "AC"    ? "from-blue-900 via-slate-900 to-slate-950" :
    chargerType === "Mixed" ? "from-purple-900 via-slate-900 to-slate-950" :
                              "from-slate-800 via-slate-900 to-slate-950";
  return (
    <div className={cn("h-36 bg-gradient-to-br relative overflow-hidden shrink-0", grad)}>
      {/* Grid pattern */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.07]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M 28 0 L 0 0 0 28" fill="none" stroke="white" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
      {/* Zeon wordmark */}
      <div className="absolute bottom-4 left-5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-md bg-primary/90 flex items-center justify-center">
          <Zap className="w-4 h-4 text-primary-foreground" />
        </div>
        <span className="text-white font-black text-2xl tracking-tight">ZEON</span>
      </div>
      {/* Connector dots decoration */}
      <div className="absolute top-4 right-6 flex gap-2">
        {[14, 10, 16].map((size, i) => (
          <div
            key={i}
            style={{ width: size, height: size }}
            className="rounded-full bg-white/20 border border-white/30"
          />
        ))}
      </div>
    </div>
  );
}

// ── Connector row ──────────────────────────────────────────────────────────────
function ConnectorRow({ c }: { c: ConnectorOut }) {
  const available = c.availability === true || c.connector_status?.toLowerCase() === "available";
  return (
    <div className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg border text-sm",
      available
        ? "bg-green-500/5 border-green-500/20"
        : "bg-muted/30 border-border/40"
    )}>
      <div className={cn(
        "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
        available ? "bg-green-500/15" : "bg-muted"
      )}>
        <Plug className={cn("w-4 h-4", available ? "text-green-400" : "text-muted-foreground")} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-xs">Connector {c.display_id ?? c.id}</p>
        {c.connector_type && (
          <p className="text-[10px] text-muted-foreground">{c.connector_type}</p>
        )}
      </div>
      <span className={cn(
        "text-[10px] font-semibold flex items-center gap-1",
        available ? "text-green-400" : "text-muted-foreground"
      )}>
        {available
          ? <><CheckCircle2 className="w-3 h-3" />Available</>
          : <><XCircle className="w-3 h-3" />Unavailable</>
        }
      </span>
    </div>
  );
}

// ── Charger card ───────────────────────────────────────────────────────────────
function ChargerCard({ ch }: { ch: ChargerOut }) {
  const [expanded, setExpanded] = useState(false);
  const typeColor =
    ch.type === "DC"    ? "bg-orange-500/15 text-orange-400 border-orange-500/30" :
    ch.type === "AC"    ? "bg-blue-500/15 text-blue-400 border-blue-500/30" :
                          "bg-primary/15 text-primary border-primary/30";

  const price = ch.price_display ?? (ch.price ? `₹ ${ch.price}` : null);

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors text-left"
      >
        <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center shrink-0">
          <Zap className="w-4.5 h-4.5 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate">{ch.charger_name ?? `Charger ${ch.id}`}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {ch.type && (
              <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded border", typeColor)}>
                {ch.type}
              </span>
            )}
            {ch.power_rating_kw && (
              <span className="text-[10px] text-muted-foreground">{parseFloat(ch.power_rating_kw)} kW</span>
            )}
          </div>
        </div>
        {price && (
          <span className="text-sm font-bold tabular-nums shrink-0">₹ {parseFloat(ch.price ?? "0").toFixed(2)}</span>
        )}
        <ChevronDown className={cn("w-4 h-4 text-muted-foreground shrink-0 transition-transform", expanded && "rotate-180")} />
      </button>

      {expanded && ch.connectors?.length > 0 && (
        <div className="px-4 pb-4 space-y-2 border-t border-border/40 pt-3">
          {ch.connectors.map((c) => <ConnectorRow key={c.id} c={c} />)}
        </div>
      )}
    </div>
  );
}

// ── Review bar ─────────────────────────────────────────────────────────────────
function ReviewBar({ stars, count, total }: { stars: number; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-3 text-muted-foreground tabular-nums">{stars}</span>
      <Star className="w-3 h-3 fill-amber-400 text-amber-400 shrink-0" />
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full bg-amber-400 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-7 text-right text-muted-foreground tabular-nums">{pct}%</span>
    </div>
  );
}

function ReviewSection({ r }: { r: ReviewSummaryOut }) {
  const avg   = r.avg_rating ? parseFloat(r.avg_rating) : 0;
  const total = r.review_count ?? 0;
  return (
    <div className="flex gap-4 items-start">
      <div className="flex flex-col items-center justify-center w-20 shrink-0">
        <span className="text-4xl font-black tabular-nums">{avg.toFixed(2)}</span>
        <Star className="w-5 h-5 fill-amber-400 text-amber-400 mt-1" />
        <span className="text-[10px] text-muted-foreground mt-1 text-center">
          Based on {total} review{total !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="flex-1 space-y-1.5">
        {([5, 4, 3, 2, 1] as const).map((n) => (
          <ReviewBar
            key={n}
            stars={n}
            count={r[`rating_${n}_count` as keyof ReviewSummaryOut] as number}
            total={total}
          />
        ))}
      </div>
    </div>
  );
}

// ── Nearby card ────────────────────────────────────────────────────────────────
function NearbyCard({ s, onSelect }: { s: NearbyStationOut; onSelect: (id: number) => void }) {
  const rating = s.avg_review_rating ? parseFloat(s.avg_review_rating) : null;
  const types: string[] = (() => {
    try { return JSON.parse(s.station_types ?? "[]"); } catch { return []; }
  })();
  return (
    <button
      onClick={() => onSelect(s.nearby_station_id)}
      className="min-w-[160px] rounded-xl border border-border bg-muted/30 p-3 text-left hover:bg-muted/60 transition-colors shrink-0"
    >
      <p className="text-xs font-semibold line-clamp-2 leading-snug mb-2">
        {s.station_name ?? `Station #${s.nearby_station_id}`}
      </p>
      <div className="flex items-center gap-1.5 flex-wrap">
        {types.slice(0, 2).map((t) => (
          <span
            key={t}
            className={cn(
              "text-[9px] font-bold px-1.5 py-0.5 rounded border",
              t === "DC" ? "bg-orange-500/15 text-orange-400 border-orange-500/30" :
              t === "AC" ? "bg-blue-500/15 text-blue-400 border-blue-500/30" :
                           "bg-primary/15 text-primary border-primary/30"
            )}
          >
            {t}
          </span>
        ))}
        {rating != null && (
          <span className="flex items-center gap-0.5 text-[10px] text-amber-400 ml-auto">
            <Star className="w-2.5 h-2.5 fill-amber-400" />{rating.toFixed(2)}
          </span>
        )}
      </div>
      <p className={cn("text-[10px] mt-1.5 font-medium",
        s.is_connected !== false ? "text-green-400" : "text-muted-foreground"
      )}>
        {s.is_connected !== false ? "Available" : "Unavailable"}
      </p>
    </button>
  );
}

// ── Main panel ─────────────────────────────────────────────────────────────────
interface Props {
  stationId: number;
  onClose:   () => void;
}

export function StationMapPanel({ stationId, onClose }: Props) {
  const { data: station, isLoading } = useStation(stationId);
  const [aboutOpen, setAboutOpen] = useState(false);

  const mapsUrl = station?.navigation_link
    ?? (station?.latitude && station?.longitude
      ? `https://www.google.com/maps/dir/?api=1&destination=${station.latitude},${station.longitude}`
      : null);

  const addressFull = [station?.address, station?.area, station?.city_name ?? station?.city_name_cached, station?.state_name]
    .filter(Boolean).join(", ");

  function copyAddress() {
    if (addressFull) navigator.clipboard?.writeText(addressFull);
  }

  return (
    <div className="absolute top-0 right-0 h-full w-[360px] z-40 flex flex-col bg-card border-l border-border shadow-2xl">

      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-3 left-3 z-10 w-8 h-8 rounded-full bg-black/50 backdrop-blur flex items-center justify-center text-white hover:bg-black/70 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">

        {/* Banner */}
        {isLoading
          ? <Skeleton className="h-36 w-full rounded-none" />
          : <Banner chargerType={station?.charger_type ?? null} />
        }

        <div className="p-4 space-y-5">

          {/* Station header */}
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
          ) : station && (
            <div>
              <h2 className="text-base font-bold leading-snug mb-1">
                {station.station_name ?? "Unknown Station"}
              </h2>
              <p className="text-xs text-muted-foreground mb-2">ID · {station.id}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn(
                  "flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full",
                  station.availability === "Available"
                    ? "bg-green-500/15 text-green-400"
                    : "bg-muted text-muted-foreground"
                )}>
                  <span className={cn(
                    "w-1.5 h-1.5 rounded-full",
                    station.availability === "Available" ? "bg-green-400" : "bg-muted-foreground"
                  )} />
                  {station.availability === "Available" ? "Open Now" : (station.availability ?? "Unknown")}
                </span>
                {station.operational_time && (
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {station.operational_time}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Chargers */}
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-14 w-full rounded-xl" />
              <Skeleton className="h-14 w-full rounded-xl" />
            </div>
          ) : station?.chargers?.length ? (
            <div className="space-y-2">
              {station.chargers.map((ch) => <ChargerCard key={ch.id} ch={ch} />)}
            </div>
          ) : null}

          {/* Address */}
          {(isLoading || addressFull) && (
            <div className="space-y-3">
              {isLoading ? (
                <Skeleton className="h-4 w-full" />
              ) : (
                <div className="flex gap-2">
                  <MapPin className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-foreground/80 leading-snug">{addressFull}</p>
                </div>
              )}
              {!isLoading && (
                <div className="flex gap-2">
                  <button
                    onClick={copyAddress}
                    className="flex-1 flex items-center justify-center gap-1.5 h-9 rounded-lg border border-border text-xs font-medium hover:bg-muted transition-colors"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Copy location
                  </button>
                  {mapsUrl && (
                    <a
                      href={mapsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 flex items-center justify-center gap-1.5 h-9 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
                    >
                      <Navigation className="w-3.5 h-3.5" />
                      Get directions
                    </a>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Amenities */}
          {!isLoading && station && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Amenities
              </p>
              {station.amenities?.length ? (
                <div className="flex flex-wrap gap-2">
                  {station.amenities.map((a) => (
                    <span key={a.id} className="text-xs px-2.5 py-1 rounded-full bg-muted border border-border">
                      {a.type}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No amenities listed for this station</p>
              )}
            </div>
          )}

          {/* Nearby stations */}
          {!isLoading && station?.nearby_stations?.length ? (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Nearby Stations
              </p>
              <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
                {station.nearby_stations.slice(0, 8).map((s) => (
                  <NearbyCard
                    key={s.nearby_station_id}
                    s={s}
                    onSelect={(id) => window.open(`/station/${id}`, "_blank")}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {/* Customer Reviews */}
          {!isLoading && station?.review_summary && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Customer Reviews
              </p>
              <div className="rounded-xl border border-border p-4">
                <ReviewSection r={station.review_summary} />
              </div>
            </div>
          )}

          {/* About this station */}
          {!isLoading && station && (
            <div className="rounded-xl border border-border overflow-hidden">
              <button
                onClick={() => setAboutOpen((v) => !v)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                  <Zap className="w-4 h-4 text-red-400" />
                </div>
                <span className="flex-1 text-sm font-semibold text-left">About this station</span>
                <ChevronDown className={cn("w-4 h-4 text-muted-foreground transition-transform", aboutOpen && "rotate-180")} />
              </button>
              {aboutOpen && (
                <div className="px-4 pb-4 border-t border-border/40 pt-3 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { icon: Shield,  label: "ACCESS",      value: station.access_type ?? "—" },
                      { icon: Clock,   label: "HOURS",       value: station.operational_time ?? "—" },
                      { icon: Zap,     label: "DC CHARGERS", value: String(station.dc_charger_count) },
                      { icon: Plug,    label: "AC CHARGERS", value: String(station.ac_charger_count) },
                    ].map(({ icon: Icon, label, value }) => (
                      <div key={label} className="rounded-lg bg-muted/40 p-3 flex items-start gap-2">
                        <Icon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                        <div>
                          <p className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</p>
                          <p className="text-sm font-semibold capitalize">{value}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {station.station_name && (
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {station.station_name} is a Zeon-tracked EV charging station
                      {station.city_name ?? station.city_name_cached
                        ? ` in ${station.city_name ?? station.city_name_cached}`
                        : ""}
                      {station.operational_time ? `, available ${station.operational_time}` : ""}.
                      Find and compare charging stations across India with Zeon CPO Tracker.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Link to full page */}
          {!isLoading && station && (
            <a
              href={`/station/${station.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center w-full h-9 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              View full station page →
            </a>
          )}

          <div className="h-4" />
        </div>
      </div>
    </div>
  );
}
