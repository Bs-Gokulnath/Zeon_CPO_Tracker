"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { useTheme } from "next-themes";

const DARK_TILE  = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const LIGHT_TILE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

const stationIcon = L.divIcon({
  html: `<div style="width:16px;height:16px;background:#22c55e;border:3px solid white;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,.5)"></div>`,
  iconSize:   [16, 16],
  iconAnchor: [8, 8],
  className:  "",
});

interface Props {
  lat:  number;
  lon:  number;
  name: string;
}

export function MiniMapInner({ lat, lon, name }: Props) {
  const { resolvedTheme } = useTheme();
  const tileUrl = resolvedTheme === "dark" ? DARK_TILE : LIGHT_TILE;

  return (
    <MapContainer
      center={[lat, lon]}
      zoom={14}
      style={{ height: "200px", width: "100%" }}
      zoomControl={false}
      attributionControl={false}
      scrollWheelZoom={false}
      dragging={false}
    >
      <TileLayer key={resolvedTheme} url={tileUrl} />
      <Marker position={[lat, lon]} icon={stationIcon}>
        <Popup closeButton={false}>
          <span className="text-xs font-medium">{name}</span>
        </Popup>
      </Marker>
    </MapContainer>
  );
}
