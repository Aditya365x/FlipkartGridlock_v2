import type { RiskLevel, AlertType } from "./types";

export function fmtDur(min?: number | null): string {
  if (min == null || Number.isNaN(min)) return "—";
  const t = Math.round(min);
  const h = Math.floor(t / 60);
  const m = t % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

export function pct(x?: number | null): string {
  if (x == null) return "—";
  return `${Math.round(x * 100)}%`;
}

// risk -> tailwind-ready hex + semantic class names
export const RISK_COLOR: Record<RiskLevel, string> = {
  LOW: "#22c55e",
  MEDIUM: "#eab308",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

export const RISK_GLOW: Record<RiskLevel, string> = {
  LOW: "shadow-[0_0_30px_-8px_rgba(34,197,94,0.5)]",
  MEDIUM: "shadow-[0_0_30px_-8px_rgba(234,179,8,0.5)]",
  HIGH: "shadow-[0_0_30px_-8px_rgba(249,115,22,0.55)]",
  CRITICAL: "shadow-[0_0_40px_-6px_rgba(239,68,68,0.65)]",
};

export const ALERT_STYLE: Record<AlertType, { ring: string; text: string; dot: string; label: string }> = {
  error: { ring: "border-danger/50 bg-danger/10", text: "text-danger", dot: "bg-danger", label: "CRITICAL" },
  warning: { ring: "border-warn/50 bg-warn/10", text: "text-warn", dot: "bg-warn", label: "WARNING" },
  info: { ring: "border-brand/50 bg-brand/10", text: "text-brand-bright", dot: "bg-brand", label: "NOTICE" },
};
