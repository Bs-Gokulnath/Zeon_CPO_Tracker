"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { useGeoPoints } from "@/hooks/useGeoPoints";
import { useFiltersParams } from "@/hooks/useFiltersParams";
import { StationMapPanel } from "@/components/map/StationMapPanel";
import { MapSearchBar } from "@/components/map/MapSearchBar";
import { Zap, MapPin, Circle } from "lucide-react";
import type { SearchHit } from "@/types/station";

const OlaMapInner = dynamic(
  () => import("@/components/map/OlaMapInner").then((m) => m.OlaMapInner),
  { ssr: false, loading: () => <Skeleton className="w-full h-full rounded-none" /> }
);

interface FlyTarget { lat: number; lng: number; zoom?: number }

export function MapsShell() {
  const { filters } = useFiltersParams();
  const { data: points = [], isLoading } = useGeoPoints(filters);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [flyTo, setFlyTo]           = useState<FlyTarget | null>(null);

  const total     = points.length;
  const available = points.filter((p) => p.availability === "Available").length;
  const ac        = points.filter((p) => p.charger_type === "AC").length;
  const dc        = points.filter((p) => p.charger_type === "DC").length;
  const mixed     = points.filter((p) => p.charger_type === "Mixed").length;

  function handleSearchSelect(hit: SearchHit) {
    // Try to find coordinates in already-loaded geo points first
    const pt = points.find((p) => p.id === hit.id);
    if (pt?.latitude && pt?.longitude) {
      setFlyTo({ lat: parseFloat(pt.latitude), lng: parseFloat(pt.longitude), zoom: 15 });
    }
    // Open the detail panel regardless (it will fetch full details)
    setSelectedId(hit.id);
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

      {/* Stats bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-border/50 bg-card/30 shrink-0 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs">
          <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="font-semibold">{isLoading ? "…" : total.toLocaleString()}</span>
          <span className="text-muted-foreground">stations</span>
        </div>
        <div className="w-px h-4 bg-border" />
        <div className="flex items-center gap-1.5 text-xs">
          <Circle className="w-3 h-3 fill-green-400 text-green-400" />
          <span className="font-semibold text-green-400">{isLoading ? "…" : available.toLocaleString()}</span>
          <span className="text-muted-foreground">available</span>
        </div>
        <div className="w-px h-4 bg-border" />
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-400 shrink-0" />
            <span className="font-medium">{ac.toLocaleString()}</span>
            <span className="text-muted-foreground">AC</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-400 shrink-0" />
            <span className="font-medium">{dc.toLocaleString()}</span>
            <span className="text-muted-foreground">DC</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 shrink-0" />
            <span className="font-medium">{mixed.toLocaleString()}</span>
            <span className="text-muted-foreground">Mixed</span>
          </span>
        </div>
        <div className="ml-auto flex items-center gap-4 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-4 rounded-full bg-green-500 inline-flex items-center justify-center text-white font-bold text-[8px]">n</span>
            Cluster (zoom to expand)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-blue-400 border border-white" />
            Single station (click for info)
          </span>
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative overflow-hidden">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-muted/20">
            <div className="flex flex-col items-center gap-3">
              <Zap className="w-8 h-8 text-primary animate-pulse" />
              <p className="text-sm text-muted-foreground">Loading station locations…</p>
            </div>
          </div>
        ) : (
          <OlaMapInner
            points={points}
            onStationClick={setSelectedId}
            flyTo={flyTo}
          />
        )}

        {/* Floating search bar */}
        {!isLoading && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 w-[420px] max-w-[calc(100vw-2rem)] z-30"
               style={{ marginRight: selectedId != null ? "360px" : "0" }}>
            <MapSearchBar onSelect={handleSearchSelect} />
          </div>
        )}

        {/* Station detail panel */}
        {selectedId != null && (
          <StationMapPanel
            stationId={selectedId}
            onClose={() => setSelectedId(null)}
          />
        )}
      </div>
        </div>
      </div>
    </div>
  );
}
