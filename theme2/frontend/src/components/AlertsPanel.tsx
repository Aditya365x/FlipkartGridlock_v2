import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import type { Alert } from "@/lib/types";
import { ALERT_STYLE } from "@/lib/format";
import { cn } from "@/lib/utils";

export function AlertsPanel({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) {
    return <div className="py-6 text-center text-sm text-ink-muted">No active alerts. ✅</div>;
  }
  return (
    <div className="space-y-2.5">
      {alerts.map((a, i) => {
        const s = ALERT_STYLE[a.type];
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06 }}
            className={cn("flex items-start gap-3 rounded-xl border px-3 py-2.5", s.ring)}
          >
            <span className="relative mt-1 flex h-2.5 w-2.5 shrink-0">
              <span className={cn("absolute inline-flex h-full w-full animate-ping2 rounded-full", s.dot)} />
              <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", s.dot)} />
            </span>
            <div className="min-w-0 flex-1">
              <div className={cn("text-[10px] font-bold uppercase tracking-wider", s.text)}>{s.label}</div>
              <div className="text-sm text-ink">{a.msg}</div>
            </div>
            <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-ink-faint" />
          </motion.div>
        );
      })}
    </div>
  );
}
