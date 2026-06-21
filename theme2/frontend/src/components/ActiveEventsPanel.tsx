import { motion } from "framer-motion";
import { Activity } from "lucide-react";
import type { ActiveEvent } from "@/lib/types";
import { RISK_COLOR, fmtDur } from "@/lib/format";

export function ActiveEventsPanel({ events }: { events: ActiveEvent[] }) {
  if (!events.length) return <div className="py-6 text-center text-sm text-ink-muted">No active events.</div>;
  return (
    <div className="space-y-2">
      {events.map((e, i) => {
        const color = RISK_COLOR[e.risk];
        return (
          <motion.div
            key={e.corridor + i}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 ${e.planned ? "border-brand/50 bg-brand/10" : "border-line bg-white/[0.03]"}`}
          >
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping2 rounded-full" style={{ backgroundColor: color }} />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-semibold text-ink">{e.corridor}</span>
                <span className="text-[10px] text-ink-faint">{e.cause}</span>
                {e.planned && <span className="rounded bg-brand/20 px-1.5 text-[9px] font-bold uppercase tracking-wide text-brand-bright">Planned</span>}
              </div>
              <div className="flex items-center gap-3 text-[11px] text-ink-muted">
                <span className="flex items-center gap-1"><Activity className="h-3 w-3" />{Math.round(e.closure_prob * 100)}% closure</span>
                <span>{fmtDur(e.impact_min)}</span>
              </div>
            </div>
            <span className="rounded-md px-2 py-1 text-[10px] font-bold" style={{ color, backgroundColor: `${color}1f` }}>
              {e.risk}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}
