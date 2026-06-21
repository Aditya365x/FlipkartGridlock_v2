import { Bell, Cloud, ShieldCheck, AlertTriangle } from "lucide-react";
import type { Alert } from "@/lib/types";

interface TopBarProps {
  criticalAlert?: Alert | null;
  notifications?: number;
}

export function TopBar({ criticalAlert, notifications = 0 }: TopBarProps) {
  return (
    <header className="flex items-center gap-4 border-b border-line bg-bg-soft/50 px-5 py-3 backdrop-blur-xl">
      {/* critical alert banner — dominant, animated */}
      {criticalAlert ? (
        <div className="relative flex flex-1 items-center gap-3 overflow-hidden rounded-xl border border-danger/50 bg-danger/10 px-4 py-2.5">
          <span className="pointer-events-none absolute inset-y-0 left-0 w-1/3 animate-sweep bg-gradient-to-r from-transparent via-danger/10 to-transparent" />
          <AlertTriangle className="h-5 w-5 shrink-0 animate-pulseDot text-danger" />
          <div className="min-w-0">
            <div className="text-[11px] font-bold uppercase tracking-wide text-danger">Critical Alert</div>
            <div className="truncate text-sm text-ink">{criticalAlert.msg}</div>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-safe/30 bg-safe/5 px-4 py-2.5">
          <ShieldCheck className="h-5 w-5 text-safe" />
          <span className="text-sm text-ink-muted">All corridors nominal — no critical alerts.</span>
        </div>
      )}

      {/* weather */}
      <div className="hidden items-center gap-2 rounded-xl border border-line bg-white/5 px-3 py-2 md:flex">
        <Cloud className="h-4 w-4 text-brand-bright" />
        <div className="leading-tight">
          <div className="text-sm font-semibold tabular-nums">28°C</div>
          <div className="text-[10px] text-ink-faint">Partly Cloudy</div>
        </div>
      </div>

      {/* notifications */}
      <button className="relative grid h-10 w-10 place-items-center rounded-xl border border-line bg-white/5 transition hover:border-brand/40">
        <Bell className="h-4 w-4 text-ink-muted" />
        {notifications > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-danger text-[10px] font-bold text-white">
            {notifications}
          </span>
        )}
      </button>

      {/* control room */}
      <div className="flex items-center gap-3 rounded-xl border border-line bg-white/5 px-3 py-2">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand to-brand-cyan text-xs font-bold text-white">
          BTP
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Control Room</div>
          <div className="text-[10px] text-ink-faint">Bengaluru Traffic Police</div>
        </div>
      </div>
    </header>
  );
}
