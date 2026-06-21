import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  FlaskConical,
  TrendingUp,
  Users,
  Map,
  Brain,
  Bell,
  FileText,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Command Center", sub: "Live overview", icon: LayoutDashboard, end: true },
  { to: "/simulation", label: "Event Planner", sub: "What-if simulation", icon: FlaskConical },
  { to: "/forecast", label: "Traffic Forecast", sub: "Hotspots & load", icon: TrendingUp },
  { to: "/resources", label: "Resource Planner", sub: "Deployment plan", icon: Users },
  { to: "/map", label: "Live Map", sub: "Real-time overview", icon: Map },
  { to: "/analytics", label: "Post-Event Learning", sub: "Analytics & insights", icon: Brain },
  { to: "/alerts", label: "Alerts Center", sub: "Active notifications", icon: Bell },
  { to: "/reports", label: "Reports", sub: "Export & logs", icon: FileText },
  { to: "/settings", label: "Settings", sub: "Configuration", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="flex w-[248px] shrink-0 flex-col border-r border-line bg-bg-soft/70 backdrop-blur-xl">
      {/* logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-brand to-brand-cyan shadow-glow">
          <ShieldCheck className="h-5 w-5 text-white" />
          <span className="absolute inset-0 rounded-xl ring-1 ring-white/20" />
        </div>
        <div className="leading-tight">
          <div className="font-display text-lg font-bold">
            EVENT <span className="text-brand-bright">Shield</span>
            <span className="ml-1 rounded bg-brand/20 px-1 text-[10px] text-brand-bright">AI</span>
          </div>
          <div className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Traffic Intelligence</div>
        </div>
      </div>

      {/* nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="block">
            {({ isActive }) => (
              <div
                className={cn(
                  "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all",
                  isActive ? "bg-brand/15 text-ink" : "text-ink-muted hover:bg-white/5 hover:text-ink",
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute left-0 top-1/2 h-7 w-1 -translate-y-1/2 rounded-r-full bg-brand-bright shadow-glow"
                  />
                )}
                <n.icon className={cn("h-[18px] w-[18px]", isActive && "text-brand-bright")} />
                <div className="leading-tight">
                  <div className="text-sm font-semibold">{n.label}</div>
                  <div className="text-[10px] text-ink-faint">{n.sub}</div>
                </div>
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* system status */}
      <div className="border-t border-line p-4">
        <div className="flex items-center gap-2 text-xs">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping2 rounded-full bg-safe" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-safe" />
          </span>
          <span className="font-semibold text-safe">System Healthy</span>
        </div>
        <Clock />
      </div>
    </aside>
  );
}

function Clock() {
  const now = new Date();
  const date = now.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
  const time = now.toLocaleTimeString("en-IN", { hour12: false });
  return (
    <div className="mt-2 font-display">
      <div className="text-2xl font-bold tabular-nums">{time}</div>
      <div className="text-[11px] text-ink-faint">{date} · Bengaluru</div>
    </div>
  );
}
