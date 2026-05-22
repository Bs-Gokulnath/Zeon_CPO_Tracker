import { Zap, Plug } from "lucide-react";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { ChargerOut, ConnectorOut } from "@/types/station";

function ConnectorBadge({ connector }: { connector: ConnectorOut }) {
  const isAvailable = connector.availability === true;
  const isError     = connector.connector_status?.toLowerCase() === "error"
    || connector.availability === false;

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
      isAvailable && !isError
        ? "bg-green-500/10 text-green-400 border-green-500/20"
        : isError
          ? "bg-red-500/10 text-red-400 border-red-500/20"
          : "bg-muted text-muted-foreground border-border"
    )}>
      <Plug className="w-2.5 h-2.5" />
      {connector.connector_type ?? `C${connector.display_id ?? connector.id}`}
    </span>
  );
}

function ChargerCard({ charger }: { charger: ChargerOut }) {
  const kw    = charger.power_rating_kw ? parseFloat(charger.power_rating_kw) : null;
  const price = charger.price_display
    ?? (charger.price ? `₹${parseFloat(charger.price).toFixed(0)}/${charger.currency ?? "kWh"}` : null);
  const allAvailable = charger.available_connector_count === charger.connector_count;

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
          <p className={cn(
            "text-xs mt-0.5",
            allAvailable ? "text-green-400" : "text-muted-foreground"
          )}>
            {charger.available_connector_count}/{charger.connector_count} available
          </p>
        </div>
      </div>

      {charger.connectors.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2.5 border-t border-border/50">
          {charger.connectors.map((c) => (
            <ConnectorBadge key={c.id} connector={c} />
          ))}
        </div>
      )}
    </div>
  );
}

interface Props { chargers: ChargerOut[] }

export function ChargingDetails({ chargers }: Props) {
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
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
        Charging Details
      </h2>
      <div className="space-y-3">
        {chargers.map((charger) => (
          <ChargerCard key={charger.id} charger={charger} />
        ))}
      </div>
    </section>
  );
}
