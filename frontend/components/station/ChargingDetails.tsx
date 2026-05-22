import { Zap, Plug } from "lucide-react";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { ChargerOut, ConnectorOut } from "@/types/station";

type LiveMap = Map<number, { available: boolean; status: string | null; error: string | null }>;

function ConnectorBadge({
  connector,
  liveMap,
}: {
  connector: ConnectorOut;
  liveMap:   LiveMap | null;
}) {
  // Use live data if available, fall back to cached
  const live        = liveMap?.get(connector.id) ?? null;
  const isAvailable = live ? live.available : connector.availability === true;
  const isLive      = live != null;

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border transition-colors",
      isAvailable
        ? "bg-green-500/10 text-green-400 border-green-500/20"
        : "bg-red-500/10 text-red-400 border-red-500/20"
    )}
    title={live?.error ?? undefined}
    >
      <Plug className="w-2.5 h-2.5" />
      {connector.connector_type ?? `C${connector.display_id ?? connector.id}`}
      {isLive && (
        <span className={cn(
          "w-1.5 h-1.5 rounded-full ml-0.5",
          isAvailable ? "bg-green-400" : "bg-red-400"
        )} />
      )}
    </span>
  );
}

function ChargerCard({ charger, liveMap }: { charger: ChargerOut; liveMap: LiveMap | null }) {
  const kw    = charger.power_rating_kw ? parseFloat(charger.power_rating_kw) : null;
  const price = charger.price_display
    ?? (charger.price ? `₹${parseFloat(charger.price).toFixed(0)}/${charger.currency ?? "kWh"}` : null);

  // Recalculate available count from live data if possible
  const liveAvailCount = liveMap && charger.connectors.length > 0
    ? charger.connectors.filter((c) => liveMap.get(c.id)?.available === true).length
    : null;
  const availCount = liveAvailCount ?? charger.available_connector_count;
  const total      = charger.connector_count;
  const allAvail   = availCount === total;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
            charger.type === "DC" ? "bg-orange-500/10" : "bg-blue-500/10"
          )}>
            <Zap className={cn(
              "w-4 h-4",
              charger.type === "DC" ? "text-orange-400" : "text-blue-400"
            )} />
          </div>
          <div>
            <p className="text-sm font-medium leading-snug">
              {charger.charger_name ?? `Charger ${charger.id}`}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <ChargerTypeBadge type={charger.type} />
              {kw != null && (
                <span className="text-xs text-muted-foreground font-medium">{kw} kW</span>
              )}
            </div>
          </div>
        </div>

        <div className="text-right shrink-0 ml-2">
          {price && <p className="text-sm font-semibold">{price}</p>}
          <p className={cn("text-xs mt-0.5", allAvail ? "text-green-400" : "text-muted-foreground")}>
            {availCount}/{total} available
          </p>
        </div>
      </div>

      {charger.connectors.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2.5 border-t border-border/50">
          {charger.connectors.map((c) => (
            <ConnectorBadge key={c.id} connector={c} liveMap={liveMap} />
          ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  chargers:         ChargerOut[];
  liveConnectorMap: LiveMap | null;
}

export function ChargingDetails({ chargers, liveConnectorMap }: Props) {
  if (chargers.length === 0) {
    return (
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Charging Details
        </h2>
        <div className="rounded-xl border border-border bg-card p-6 text-center text-sm text-muted-foreground">
          No charger details available.
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Charging Details
        </h2>
        {liveConnectorMap && liveConnectorMap.size > 0 && (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-green-400 bg-green-500/10 border border-green-500/20 px-1.5 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            LIVE
          </span>
        )}
      </div>
      <div className="space-y-3">
        {chargers.map((charger) => (
          <ChargerCard key={charger.id} charger={charger} liveMap={liveConnectorMap} />
        ))}
      </div>
    </section>
  );
}
