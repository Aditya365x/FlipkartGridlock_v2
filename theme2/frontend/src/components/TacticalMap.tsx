import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";

export interface MapMarker {
  label: string;
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  x: number; // 0-100 (% of width)
  y: number; // 0-100 (% of height)
}

const SEV_COLOR: Record<MapMarker["severity"], string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MODERATE: "#eab308",
  LOW: "#22c55e",
};

// deterministic pseudo-position from a string, so corridors land in stable spots
export function posFor(name: string): { x: number; y: number } {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return { x: 18 + (h % 1000) / 1000 * 64, y: 18 + ((h >> 10) % 1000) / 1000 * 60 };
}

/**
 * Stylised "tactical" map: a dark city plate with radial roads, glow, and live event markers.
 * Self-contained SVG (no Mapbox token / no network) so it renders identically in any demo.
 * Swap for <MapContainer> from react-leaflet with CARTO dark tiles if live tiles are desired.
 */
export function TacticalMap({ markers, center = "Bengaluru" }: { markers: MapMarker[]; center?: string }) {
  return (
    <div className="relative h-full min-h-[420px] w-full overflow-hidden rounded-2xl border border-line bg-[#060a13]">
      {/* base glow + grid */}
      <div className="absolute inset-0 tactical-grid opacity-60" />
      <div className="absolute inset-0 bg-[radial-gradient(600px_300px_at_50%_40%,rgba(37,99,235,0.12),transparent_70%)]" />

      {/* roads */}
      <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none" viewBox="0 0 100 100">
        {[...Array(8)].map((_, i) => {
          const a = (i / 8) * Math.PI * 2;
          return (
            <line
              key={i}
              x1="50"
              y1="50"
              x2={50 + Math.cos(a) * 60}
              y2={50 + Math.sin(a) * 60}
              stroke="rgba(96,165,250,0.16)"
              strokeWidth="0.4"
            />
          );
        })}
        {[14, 26, 38].map((r) => (
          <circle key={r} cx="50" cy="50" r={r} fill="none" stroke="rgba(96,165,250,0.12)" strokeWidth="0.3" />
        ))}
      </svg>

      {/* city label */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 select-none font-display text-lg font-bold text-ink/30">
        {center}
      </div>

      {/* markers */}
      {markers.map((m, i) => {
        const color = SEV_COLOR[m.severity];
        const critical = m.severity === "CRITICAL";
        return (
          <motion.div
            key={m.label + i}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.08 }}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${m.x}%`, top: `${m.y}%` }}
          >
            <div className="relative grid place-items-center">
              <span className="absolute h-8 w-8 animate-ping2 rounded-full" style={{ backgroundColor: `${color}40` }} />
              <span
                className="relative grid h-6 w-6 place-items-center rounded-full ring-2 ring-white/30"
                style={{ backgroundColor: color, boxShadow: `0 0 14px ${color}` }}
              >
                {critical && <AlertTriangle className="h-3.5 w-3.5 text-white" />}
              </span>
              <span className="mt-1 whitespace-nowrap rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-ink backdrop-blur">
                {m.label}
              </span>
            </div>
          </motion.div>
        );
      })}

      {/* legend */}
      <div className="absolute bottom-3 left-3 flex gap-3 rounded-lg border border-line bg-black/40 px-3 py-2 backdrop-blur">
        {(["CRITICAL", "HIGH", "MODERATE", "LOW"] as const).map((s) => (
          <div key={s} className="flex items-center gap-1.5 text-[10px] text-ink-muted">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: SEV_COLOR[s] }} />
            {s}
          </div>
        ))}
      </div>
    </div>
  );
}
