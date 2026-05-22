"use client";

import { useState, useRef, useEffect } from "react";
import { Search, X, Zap, Plug, Star, MapPin, Clock, Shield, ChevronRight } from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { useAutocomplete } from "@/hooks/useSearch";
import { useStation } from "@/hooks/useStation";
import { useDebounce } from "@/hooks/useDebounce";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { StationDetail, SearchHit } from "@/types/station";

// ── Station Picker ────────────────────────────────────────────────────────────
function StationPicker({
  label,
  selectedId,
  onSelect,
  onClear,
}: {
  label: string;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onClear: () => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const debounced = useDebounce(q, 250);
  const { data: hits = [] } = useAutocomplete(debounced);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function pick(hit: SearchHit) {
    onSelect(hit.id);
    setQ("");
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">{label}</p>
      {selectedId ? (
        <button
          onClick={onClear}
          className="flex items-center gap-2 w-full px-3 h-9 rounded-lg border border-primary/40 bg-primary/5 text-sm hover:bg-destructive/10 hover:border-destructive/40 transition-colors group"
        >
          <span className="flex-1 text-left truncate text-foreground">Station #{selectedId}</span>
          <X className="w-3.5 h-3.5 text-muted-foreground group-hover:text-destructive shrink-0" />
        </button>
      ) : (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)}
            placeholder="Search station…"
            className="w-full h-9 pl-8 pr-3 rounded-lg border border-border bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
          />
        </div>
      )}

      {open && hits.length > 0 && !selectedId && (
        <div className="absolute z-50 top-full mt-1 w-full bg-popover border border-border rounded-lg shadow-xl overflow-hidden">
          {hits.map((hit) => (
            <button
              key={hit.id}
              onClick={() => pick(hit)}
              className="flex items-start gap-2 w-full px-3 py-2 text-left hover:bg-accent transition-colors"
            >
              <div className="min-w-0">
                <p className="text-xs font-medium truncate">{hit.station_name ?? "Unknown"}</p>
                <p className="text-[10px] text-muted-foreground truncate">
                  {[hit.city_name, hit.state_name].filter(Boolean).join(", ")}
                  {hit.charger_type && <span className="ml-1.5 opacity-60">{hit.charger_type}</span>}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Comparison column ─────────────────────────────────────────────────────────
function StationColumn({ id }: { id: number }) {
  const { data: station, isLoading } = useStation(id);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-32 bg-muted rounded-xl" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 bg-muted rounded-lg" />
        ))}
      </div>
    );
  }

  if (!station) return null;
  return <StationDetails station={station} />;
}

function StationDetails({ station }: { station: StationDetail }) {
  const rating = station.avg_rating ? parseFloat(station.avg_rating) : null;
  const is24h = station.operational_time?.toLowerCase().includes("24") ?? false;
  const acPrice = station.min_ac_price ? `₹${parseFloat(station.min_ac_price).toFixed(0)}` : null;
  const dcPrice = station.min_dc_price ? `₹${parseFloat(station.min_dc_price).toFixed(0)}` : null;

  return (
    <div className="space-y-4">
      {/* Hero card */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className={cn(
          "h-28 bg-gradient-to-br relative",
          station.charger_type === "DC" ? "from-orange-950/60 to-slate-900" :
          station.charger_type === "AC" ? "from-blue-950/60 to-slate-900" :
          "from-purple-950/60 to-slate-900"
        )}>
          <div className="absolute inset-0 flex items-center justify-center opacity-10">
            <Zap className="w-20 h-20" />
          </div>
          <div className="absolute top-3 left-3 flex gap-2">
            <ChargerTypeBadge type={station.charger_type} />
          </div>
          {station.highest_power_kw && (
            <div className="absolute top-3 right-3 bg-black/60 backdrop-blur text-white text-xs font-bold px-2 py-0.5 rounded-full">
              ⚡ {parseFloat(station.highest_power_kw)} kW
            </div>
          )}
        </div>
        <div className="p-3">
          <h3 className="font-semibold text-sm leading-snug mb-1">{station.station_name ?? "—"}</h3>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="w-3 h-3 shrink-0" />
            <span className="truncate">
              {[station.city_name ?? station.city_name_cached, station.state_name].filter(Boolean).join(", ")}
            </span>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-2">
        <StatBox label="Status">
          <StatusBadge availability={station.availability} />
        </StatBox>
        <StatBox label="Rating">
          {rating != null ? (
            <span className="flex items-center gap-1 text-sm font-semibold">
              <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              {rating.toFixed(1)}
              <span className="text-xs text-muted-foreground font-normal">({station.review_count ?? 0})</span>
            </span>
          ) : <span className="text-xs text-muted-foreground">No ratings</span>}
        </StatBox>
        <StatBox label="Chargers">
          <span className="text-sm font-semibold">{station.total_charger_count}</span>
          <span className="text-xs text-muted-foreground ml-1">
            ({station.ac_charger_count} AC · {station.dc_charger_count} DC)
          </span>
        </StatBox>
        <StatBox label="Connectors">
          <span className={cn("text-sm font-semibold", station.available_connector_count > 0 ? "text-green-400" : "text-muted-foreground")}>
            {station.available_connector_count}
          </span>
          <span className="text-xs text-muted-foreground ml-1">/ {station.total_connector_count} free</span>
        </StatBox>
        <StatBox label="AC Price">
          <span className="text-sm font-semibold">{acPrice ? `${acPrice}/kWh` : "—"}</span>
        </StatBox>
        <StatBox label="DC Price">
          <span className="text-sm font-semibold">{dcPrice ? `${dcPrice}/kWh` : "—"}</span>
        </StatBox>
        <StatBox label="Access">
          <span className="flex items-center gap-1 text-xs">
            <Shield className="w-3 h-3" />
            {station.access_type ?? "—"}
          </span>
        </StatBox>
        <StatBox label="Hours">
          <span className="flex items-center gap-1 text-xs">
            <Clock className="w-3 h-3" />
            {is24h ? <span className="text-green-400 font-medium">24/7</span> : (station.operational_time ?? "—")}
          </span>
        </StatBox>
      </div>

      {/* Chargers */}
      {station.chargers.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Chargers</p>
          <div className="space-y-2">
            {station.chargers.map((c) => (
              <div key={c.id} className="rounded-lg border border-border bg-card/50 px-3 py-2 flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate">{c.charger_name ?? `Charger ${c.id}`}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <ChargerTypeBadge type={c.type} />
                    {c.power_rating_kw && <span className="text-[10px] text-muted-foreground">{parseFloat(c.power_rating_kw)} kW</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  {c.price_display && <p className="text-xs font-semibold">{c.price_display}</p>}
                  <p className={cn("text-[10px]", c.available_connector_count > 0 ? "text-green-400" : "text-muted-foreground")}>
                    {c.available_connector_count}/{c.connector_count} free
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View full details */}
      <Link
        href={`/station/${station.id}`}
        className="flex items-center justify-center gap-1.5 w-full h-9 rounded-lg border border-border text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        View full details
        <ChevronRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}

function StatBox({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card/50 px-3 py-2">
      <p className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wider">{label}</p>
      <div className="flex items-center flex-wrap">{children}</div>
    </div>
  );
}

// ── Main shell ────────────────────────────────────────────────────────────────
export function CompareShell() {
  const [idA, setIdA] = useState<number | null>(null);
  const [idB, setIdB] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold mb-1">Compare Stations</h1>
          <p className="text-sm text-muted-foreground">Search and select two stations to compare them side by side.</p>
        </div>

        {/* Pickers */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <StationPicker label="Station A" selectedId={idA} onSelect={setIdA} onClear={() => setIdA(null)} />
          <StationPicker label="Station B" selectedId={idB} onSelect={setIdB} onClear={() => setIdB(null)} />
        </div>

        {/* Empty state */}
        {!idA && !idB && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-muted-foreground" />
            </div>
            <p className="text-sm font-medium mb-1">Select two stations above</p>
            <p className="text-xs text-muted-foreground">Search by name, city, or operator</p>
          </div>
        )}

        {/* Comparison columns */}
        {(idA || idB) && (
          <div className="grid grid-cols-2 gap-6">
            <div>
              {idA ? (
                <StationColumn id={idA} />
              ) : (
                <EmptySlot />
              )}
            </div>
            <div>
              {idB ? (
                <StationColumn id={idB} />
              ) : (
                <EmptySlot />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptySlot() {
  return (
    <div className="h-48 rounded-xl border border-dashed border-border flex items-center justify-center text-sm text-muted-foreground">
      Select a station above
    </div>
  );
}
