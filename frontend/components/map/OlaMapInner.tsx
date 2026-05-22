"use client";

import { useEffect, useRef } from "react";
import type { MapPoint } from "@/types/station";

const API_KEY   = process.env.NEXT_PUBLIC_OLA_API_KEY ?? "";
const STYLE_URL = `https://api.olamaps.io/tiles/vector/v1/styles/default-dark-standard/style.json?api_key=${API_KEY}`;

const TYPE_COLOR: Record<string, string> = {
  AC:    "#60a5fa",
  DC:    "#fb923c",
  Mixed: "#c084fc",
};

function toGeoJSON(points: MapPoint[]) {
  return {
    type: "FeatureCollection" as const,
    features: points
      .filter((p) => p.latitude != null && p.longitude != null)
      .map((p) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [parseFloat(String(p.longitude)), parseFloat(String(p.latitude))],
        },
        properties: {
          id:           p.id,
          availability: p.availability ?? "",
          charger_type: p.charger_type ?? "",
          color:        TYPE_COLOR[p.charger_type ?? ""] ?? "#94a3b8",
        },
      })),
  };
}

interface Props {
  points:          MapPoint[];
  onStationClick?: (id: number) => void;
  flyTo?:          { lat: number; lng: number; zoom?: number } | null;
}

export function OlaMapInner({ points, onStationClick, flyTo }: Props) {
  const containerRef      = useRef<HTMLDivElement>(null);
  const mapRef            = useRef<any>(null);
  const onClickRef        = useRef(onStationClick);
  onClickRef.current      = onStationClick;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    let map: any;

    function olaUrl(url: string) {
      if (!url.includes("olamaps.io")) return url;
      const clean = url.replace(/([?&])key=[^&]*/g, "$1").replace(/[?&]$/, "");
      const sep   = clean.includes("?") ? "&" : "?";
      return `${clean}${sep}api_key=${API_KEY}`;
    }

    async function fetchStyle() {
      const res   = await fetch(olaUrl(STYLE_URL));
      const style = await res.json();

      // Patch tile source URLs to carry the API key
      if (style.sources) {
        for (const src of Object.values(style.sources) as any[]) {
          if (src.url)   src.url   = olaUrl(src.url);
          if (src.tiles) src.tiles = src.tiles.map(olaUrl);
        }
      }

      // Remove layers whose source-layer doesn't exist in the tile data
      const BROKEN = new Set(["3d_model", "3d_model_data"]);
      if (style.layers) {
        style.layers = style.layers.filter(
          (l: any) => !BROKEN.has(l.id) && !BROKEN.has(l["source-layer"])
        );
      }

      return style;
    }

    async function init() {
      const mgl   = await import("maplibre-gl");
      const style = await fetchStyle();

      map = new mgl.Map({
        container: containerRef.current!,
        style,
        center:    [78.9629, 20.5937],
        zoom:      4.5,
        attributionControl: false,
        transformRequest: (url: string) => ({ url: olaUrl(url) }),
      });

      map.addControl(new mgl.NavigationControl({ showCompass: true }), "top-right");
      map.addControl(new mgl.ScaleControl({ unit: "metric" }), "bottom-left");
      map.addControl(
        new mgl.AttributionControl({ compact: true, customAttribution: "Ola Maps" }),
        "bottom-right",
      );

      map.on("load", () => {
        map.addSource("stations", {
          type:          "geojson",
          data:          toGeoJSON(points),
          cluster:       true,
          clusterMaxZoom: 13,
          clusterRadius:  45,
        });

        // Cluster bubble
        map.addLayer({
          id:     "clusters",
          type:   "circle",
          source: "stations",
          filter: ["has", "point_count"],
          paint:  {
            "circle-color": [
              "step", ["get", "point_count"],
              "#22c55e", 30,
              "#f59e0b", 150,
              "#ef4444",
            ],
            "circle-radius":       ["step", ["get", "point_count"], 18, 30, 26, 150, 34],
            "circle-stroke-width": 2,
            "circle-stroke-color": "rgba(255,255,255,0.6)",
            "circle-opacity":      0.9,
          },
        });

        // Cluster count text
        map.addLayer({
          id:     "cluster-count",
          type:   "symbol",
          source: "stations",
          filter: ["has", "point_count"],
          layout: {
            "text-field": ["get", "point_count_abbreviated"],
            "text-size":  12,
          },
          paint: { "text-color": "#ffffff", "text-halo-color": "rgba(0,0,0,0.3)", "text-halo-width": 1 },
        });

        // Individual dots — coloured by charger type
        map.addLayer({
          id:     "stations-dot",
          type:   "circle",
          source: "stations",
          filter: ["!", ["has", "point_count"]],
          paint:  {
            "circle-color":        ["get", "color"],
            "circle-radius":       7,
            "circle-stroke-width": 1.5,
            "circle-stroke-color": "rgba(255,255,255,0.8)",
            "circle-opacity":      0.95,
          },
        });

        // Cursor
        map.on("mouseenter", "clusters",   () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "clusters",   () => (map.getCanvas().style.cursor = ""));
        map.on("mouseenter", "stations-dot", () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "stations-dot", () => (map.getCanvas().style.cursor = ""));

        // Cluster click → zoom
        map.on("click", "clusters", (e: any) => {
          const [feat] = map.queryRenderedFeatures(e.point, { layers: ["clusters"] });
          const src    = map.getSource("stations");
          src.getClusterExpansionZoom(feat.properties.cluster_id, (err: any, zoom: number) => {
            if (err) return;
            map.easeTo({ center: feat.geometry.coordinates, zoom });
          });
        });

        // Dot click → open side panel
        map.on("click", "stations-dot", (e: any) => {
          const [feat] = map.queryRenderedFeatures(e.point, { layers: ["stations-dot"] });
          if (!feat) return;
          onClickRef.current?.(feat.properties.id);
        });
      });

      mapRef.current = map;
    }

    init();

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync points after load
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded?.()) return;
    map.getSource("stations")?.setData(toGeoJSON(points));
  }, [points]);

  // Fly to a station when selected from search
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyTo) return;
    map.flyTo({ center: [flyTo.lng, flyTo.lat], zoom: flyTo.zoom ?? 15, duration: 1200 });
  }, [flyTo]);

  return <div ref={containerRef} className="w-full h-full" />;
}
