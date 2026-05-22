"use client";

import { useMemo } from "react";
import { AlertCircle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Navbar }                from "@/components/layout/Navbar";
import { StationHero }           from "@/components/station/StationHero";
import { ChargingDetails }       from "@/components/station/ChargingDetails";
import { NearbyStations }        from "@/components/station/NearbyStations";
import { MiniMap }               from "@/components/station/MiniMap";
import { ReviewSummary }         from "@/components/station/ReviewSummary";
import { StationDetailSkeleton } from "@/components/station/StationDetailSkeleton";
import { useStation }            from "@/hooks/useStation";
import { useLiveStatus }         from "@/hooks/useLiveStatus";
import type { LiveStatus }       from "@/types/station";

interface Props { id: number }

export function StationDetailShell({ id }: Props) {
  const { data: station, isLoading, isError } = useStation(id);
  const { data: live, isLoading: liveLoading, isError: liveError } = useLiveStatus(id);

  // Build a map of connector_id → live status for O(1) lookup in ChargingDetails
  const liveConnectorMap = useMemo(() => {
    if (!live?.connectors) return null;
    const map = new Map<number, { available: boolean; status: string | null; error: string | null }>();
    for (const c of live.connectors) {
      if (c.connector_id != null) map.set(c.connector_id, { available: c.available, status: c.status, error: c.error });
    }
    return map;
  }, [live]);

  if (isLoading) return <StationDetailSkeleton />;

  if (isError || !station) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center min-h-[calc(100vh-3.5rem)]">
          <div className="text-center space-y-4 max-w-sm px-4">
            <div className="w-14 h-14 rounded-full bg-destructive/10 flex items-center justify-center mx-auto">
              <AlertCircle className="w-7 h-7 text-destructive" />
            </div>
            <h2 className="text-xl font-semibold">Station not found</h2>
            <p className="text-sm text-muted-foreground">
              This station doesn&apos;t exist or may have been removed.
            </p>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 px-4 h-9 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const lat = station.latitude  ? parseFloat(station.latitude)  : null;
  const lon = station.longitude ? parseFloat(station.longitude) : null;

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="container max-w-6xl mx-auto px-4 py-6 space-y-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Dashboard
        </Link>

        <StationHero
          station={station}
          liveStatus={live ?? null}
          liveLoading={liveLoading}
          liveError={liveError}
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <ChargingDetails
              chargers={station.chargers}
              liveConnectorMap={liveConnectorMap}
            />
            <ReviewSummary summary={station.review_summary} />
          </div>

          <div className="space-y-6">
            {lat != null && lon != null && (
              <MiniMap lat={lat} lon={lon} name={station.station_name ?? "Station"} />
            )}
          </div>
        </div>

        {station.nearby_stations.length > 0 && (
          <NearbyStations nearby={station.nearby_stations} />
        )}
      </div>
    </div>
  );
}
