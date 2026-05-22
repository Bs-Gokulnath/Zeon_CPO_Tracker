import Link from "next/link";
import { Star, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NearbyStationOut } from "@/types/station";

function NearbyCard({ station }: { station: NearbyStationOut }) {
  const rating    = station.avg_review_rating ? parseFloat(station.avg_review_rating) : null;
  const hasDC     = station.station_types?.includes("DC") ?? false;
  const isOnline  = station.is_connected !== false;

  return (
    <Link
      href={`/station/${station.nearby_station_id}`}
      className="shrink-0 w-44 rounded-xl border border-border bg-card p-3 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5 transition-all duration-200 block"
    >
      <div className={cn(
        "h-14 rounded-lg mb-2.5 bg-gradient-to-br relative overflow-hidden",
        hasDC ? "from-orange-950/40 to-slate-900/80" : "from-blue-950/40 to-slate-900/80"
      )}>
        <div className="absolute inset-0 flex items-center justify-center opacity-20">
          <Zap className="w-5 h-5" />
        </div>
        <div className={cn(
          "absolute top-1.5 right-1.5 w-2 h-2 rounded-full",
          isOnline ? "bg-green-400" : "bg-amber-400"
        )} />
      </div>

      <p className="text-xs font-medium line-clamp-2 leading-snug mb-1.5 min-h-[2rem]">
        {station.station_name ?? "Unknown Station"}
      </p>

      <div className="flex items-center justify-between">
        {rating != null ? (
          <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
            <Star className="w-2.5 h-2.5 fill-amber-400 text-amber-400" />
            {rating.toFixed(1)}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
        {station.station_types && (
          <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded font-medium">
            {station.station_types}
          </span>
        )}
      </div>
    </Link>
  );
}

interface Props { nearby: NearbyStationOut[] }

export function NearbyStations({ nearby }: Props) {
  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
        Nearby Stations
      </h2>
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin -mx-4 px-4 lg:mx-0 lg:px-0">
        {nearby.map((s) => (
          <NearbyCard key={s.nearby_station_id} station={s} />
        ))}
      </div>
    </section>
  );
}
