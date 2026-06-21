import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon: ReactNode;
  accent?: "brand" | "danger" | "warn" | "amber" | "safe";
  delay?: number;
}

const ACCENT: Record<NonNullable<KpiCardProps["accent"]>, { text: string; ring: string; glow: string }> = {
  brand: { text: "text-brand-bright", ring: "from-brand/20", glow: "group-hover:shadow-glow" },
  danger: { text: "text-danger", ring: "from-danger/20", glow: "group-hover:shadow-glow-danger" },
  warn: { text: "text-warn", ring: "from-warn/20", glow: "" },
  amber: { text: "text-amber", ring: "from-amber/20", glow: "" },
  safe: { text: "text-safe", ring: "from-safe/20", glow: "" },
};

export function KpiCard({ label, value, sub, icon, accent = "brand", delay = 0 }: KpiCardProps) {
  const a = ACCENT[accent];
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={cn("group glass relative overflow-hidden p-4 transition-all duration-300", a.glow)}
    >
      <div className={cn("pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br to-transparent blur-2xl", a.ring)} />
      <div className="flex items-start justify-between">
        <span className="panel-title">{label}</span>
        <span className={cn("rounded-lg bg-white/5 p-1.5", a.text)}>{icon}</span>
      </div>
      <div className={cn("kpi-value mt-3", a.text)}>{value}</div>
      {sub && <div className="mt-1.5 text-[11px] text-ink-muted">{sub}</div>}
    </motion.div>
  );
}
