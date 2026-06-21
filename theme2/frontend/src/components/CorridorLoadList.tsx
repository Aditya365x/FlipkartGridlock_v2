import { motion } from "framer-motion";
import type { CorridorLoad } from "@/lib/types";

function levelFor(v: number, max: number): { label: string; color: string } {
  const r = max > 0 ? v / max : 0;
  if (r >= 0.85) return { label: "CRITICAL", color: "#ef4444" };
  if (r >= 0.6) return { label: "HIGH", color: "#f97316" };
  if (r >= 0.3) return { label: "MODERATE", color: "#eab308" };
  return { label: "LOW", color: "#22c55e" };
}

export function CorridorLoadList({ corridors, max }: { corridors: CorridorLoad[]; max?: number }) {
  const mx = max ?? Math.max(...corridors.map((c) => c.expected_load), 0.01);
  return (
    <div className="space-y-3">
      {corridors.map((c, i) => {
        const lvl = levelFor(c.expected_load, mx);
        return (
          <div key={c.corridor}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="text-ink-faint tabular-nums">{i + 1}</span>
                <span className="font-medium text-ink">{c.corridor}</span>
              </span>
              <span className="flex items-center gap-2">
                <span className="tabular-nums text-ink-muted">{c.expected_load.toFixed(2)}</span>
                <span
                  className="rounded px-1.5 py-0.5 text-[10px] font-bold"
                  style={{ color: lvl.color, backgroundColor: `${lvl.color}1f` }}
                >
                  {lvl.label}
                </span>
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: lvl.color, boxShadow: `0 0 10px ${lvl.color}` }}
                initial={{ width: 0 }}
                animate={{ width: `${(c.expected_load / mx) * 100}%` }}
                transition={{ duration: 0.7, delay: i * 0.05 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
