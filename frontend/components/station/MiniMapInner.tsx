"use client";

import { useEffect, useRef } from "react";

const API_KEY   = process.env.NEXT_PUBLIC_OLA_API_KEY ?? "";
const STYLE_URL = `https://api.olamaps.io/tiles/vector/v1/styles/default-dark-standard/style.json?api_key=${API_KEY}`;

interface Props {
  lat:  number;
  lon:  number;
  name: string;
}

function olaUrl(url: string) {
  if (!url.includes("olamaps.io")) return url;
  const clean = url.replace(/([?&])key=[^&]*/g, "$1").replace(/[?&]$/, "");
  const sep   = clean.includes("?") ? "&" : "?";
  return `${clean}${sep}api_key=${API_KEY}`;
}

async function fetchStyle() {
  const res   = await fetch(olaUrl(STYLE_URL));
  const style = await res.json();
  if (style.sources) {
    for (const src of Object.values(style.sources) as any[]) {
      if (src.url)   src.url   = olaUrl(src.url);
      if (src.tiles) src.tiles = src.tiles.map(olaUrl);
    }
  }
  const BROKEN = new Set(["3d_model", "3d_model_data"]);
  if (style.layers) {
    style.layers = style.layers.filter(
      (l: any) => !BROKEN.has(l.id) && !BROKEN.has(l["source-layer"])
    );
  }
  return style;
}

export function MiniMapInner({ lat, lon, name }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    async function init() {
      const mgl   = await import("maplibre-gl");
      const style = await fetchStyle();

      const map = new mgl.Map({
        container:          containerRef.current!,
        style,
        center:             [lon, lat],
        zoom:               14,
        attributionControl: false,
        transformRequest:   (url: string) => ({ url: olaUrl(url) }),
      });

      map.addControl(new mgl.NavigationControl({ showCompass: false }), "top-right");

      map.on("load", () => {
        // Station marker as a GeoJSON point
        map.addSource("station", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: [{
              type: "Feature",
              geometry: { type: "Point", coordinates: [lon, lat] },
              properties: { name },
            }],
          },
        });

        // Outer pulse ring
        map.addLayer({
          id:     "station-pulse",
          type:   "circle",
          source: "station",
          paint:  {
            "circle-radius":       16,
            "circle-color":        "#22c55e",
            "circle-opacity":      0.2,
            "circle-stroke-width": 0,
          },
        });

        // Main dot
        map.addLayer({
          id:     "station-dot",
          type:   "circle",
          source: "station",
          paint:  {
            "circle-radius":       9,
            "circle-color":        "#22c55e",
            "circle-stroke-width": 3,
            "circle-stroke-color": "#ffffff",
            "circle-opacity":      1,
          },
        });

        // Label
        map.addLayer({
          id:     "station-label",
          type:   "symbol",
          source: "station",
          layout: {
            "text-field":  ["get", "name"],
            "text-size":   11,
            "text-offset": [0, 1.8],
            "text-anchor": "top",
          },
          paint: {
            "text-color":      "#ffffff",
            "text-halo-color": "rgba(0,0,0,0.8)",
            "text-halo-width": 1.5,
          },
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

  return <div ref={containerRef} style={{ height: "220px", width: "100%" }} />;
}
