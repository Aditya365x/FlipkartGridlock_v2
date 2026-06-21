import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import type { CorridorLoad } from "@/lib/types";

export interface GeoMarker extends CorridorLoad {
  lat?: number;
  lon?: number;
}

const BLR: [number, number] = [12.9716, 77.5946];

function sevColor(v: number, max: number) {
  const r = max > 0 ? v / max : 0;
  if (r >= 0.85) return "#ef4444";
  if (r >= 0.6) return "#f97316";
  if (r >= 0.3) return "#eab308";
  return "#22c55e";
}

/**
 * Real pan/zoom map (Leaflet + CARTO dark tiles, no token needed). Plots corridors at their
 * true coordinates with severity-colored, load-scaled markers. Tiles require internet at runtime.
 */
export function LiveMapView({ markers, height = 460 }: { markers: GeoMarker[]; height?: number | string }) {
  const pts = markers.filter((m) => m.lat != null && m.lon != null);
  const max = Math.max(...pts.map((m) => m.expected_load), 0.01);

  return (
    <div className="h-full overflow-hidden rounded-2xl border border-line" style={{ height, minHeight: 380 }}>
      <MapContainer center={BLR} zoom={11} scrollWheelZoom className="h-full w-full" style={{ background: "#060a13" }}>
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap contributors'
        />
        {pts.map((m, i) => {
          const color = sevColor(m.expected_load, max);
          const radius = 8 + (m.expected_load / max) * 18;
          return (
            <CircleMarker
              key={m.corridor + i}
              center={[m.lat!, m.lon!]}
              radius={radius}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.55, weight: 2 }}
            >
              <Tooltip permanent direction="top" offset={[0, -radius - 2]} opacity={1} className="es-label">
                <span className="font-semibold">{m.corridor}</span>
                <span className="ml-1 opacity-70">{m.expected_load.toFixed(2)}</span>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
