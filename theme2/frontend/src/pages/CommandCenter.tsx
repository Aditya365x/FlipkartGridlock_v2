import {
  Activity,
   Construction,
  Clock,
  Users,
  ShieldCheck,
  AlertTriangle,
  Map as MapIcon,
  ListChecks,
  TrendingUp,
  RadioTower,
  RefreshCw,
} from "lucide-react";
import { useDashboard } from "@/lib/dashboard";
import { useScenario } from "@/lib/scenario";
import type { ActiveEvent } from "@/lib/types";
import { fmtDur, pct, RISK_COLOR } from "@/lib/format";
import { KpiCard } from "@/components/KpiCard";
import { RiskMeter } from "@/components/RiskMeter";
import { AlertsPanel } from "@/components/AlertsPanel";
import { ActiveEventsPanel } from "@/components/ActiveEventsPanel";
import { ActionPlanCard } from "@/components/ActionPlanCard";
import { CorridorLoadList } from "@/components/CorridorLoadList";
import { LiveMapView } from "@/components/LiveMapView";
import { Panel } from "@/components/ui/Panel";
import { Loading, ErrorState } from "@/components/ui/StateView";

export default function CommandCenter() {
  // shared, polled source (also drives the top alert banner — single source of truth)
  const { data, loading, error, reload } = useDashboard();
  const { scenario } = useScenario();

  if (loading) return <Loading label="Initializing command center…" />;
  if (error || !data) return <ErrorState msg={error ?? "No data"} onRetry={reload} />;

  const affected = data.top_corridors.filter((c) => c.expected_load > 0).length;
  const updated = data.generated_at ? new Date(data.generated_at).toLocaleTimeString("en-IN", { hour12: false }) : "—";

  // inject the user's planned event (from Event Planner) at the top of the live roster
  const plannedEvent: ActiveEvent | null = scenario
    ? {
        corridor: scenario.input.corridor,
        cause: scenario.input.event_cause,
        event_type: scenario.input.event_type,
        expected_load: 0,
        risk: scenario.result.decision.risk.level,
        score: scenario.result.decision.risk.score,
        closure_prob: scenario.result.prediction.road_closure_prob,
        needs_barricade: scenario.result.prediction.needs_barricade,
        impact_min: scenario.result.prediction.expected_duration_min,
        planned: true,
      }
    : null;
  const roster: ActiveEvent[] = plannedEvent
    ? [plannedEvent, ...(data.active_events ?? []).filter((e) => e.corridor !== plannedEvent.corridor)]
    : data.active_events ?? [];

  return (
    <div className="space-y-5">
      {/* PAGE HEADER — honest 'simulated feed' label + live clock */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold">Command Center</h1>
          <p className="text-sm text-ink-muted">
            City-wide operational picture · {roster.length} active events
            {plannedEvent && <span className="text-brand-bright"> · incl. your planned event</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full border border-amber/40 bg-amber/10 px-3 py-1.5 text-[11px] font-semibold text-amber">
            <RadioTower className="h-3.5 w-3.5" /> SIMULATED FEED · model-derived
          </span>
          <button onClick={reload} className="flex items-center gap-1.5 rounded-xl border border-line bg-white/5 px-3 py-1.5 text-xs text-ink-muted transition hover:border-brand/40">
            <RefreshCw className="h-3.5 w-3.5" /> Updated {updated}
          </button>
        </div>
      </div>

      {/* KPI ROW */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Overall Status"
          value={data.status}
          sub={`Impact score ${data.impact_score.toFixed(0)}/100`}
          icon={<AlertTriangle className="h-4 w-4" />}
          accent={data.status === "CRITICAL" || data.status === "HIGH" ? "danger" : data.status === "MEDIUM" ? "amber" : "safe"}
          delay={0.02}
        />
        <KpiCard label="Road-Closure Risk" value={pct(data.closure_prob)} sub={data.needs_barricade ? "Barricades recommended" : "No closure expected"} icon={<Construction className="h-4 w-4" />} accent={data.needs_barricade ? "warn" : "brand"} delay={0.06} />
        <KpiCard label="Expected Impact" value={fmtDur(data.expected_impact_min)} sub="Traffic-disruption window" icon={<Clock className="h-4 w-4" />} accent="brand" delay={0.1} />
        <KpiCard label="Officers Deployed" value={`${data.officers.deployed}/${data.officers.total}`} sub="Event corridor allocation" icon={<Users className="h-4 w-4" />} accent="brand" delay={0.14} />
        <KpiCard label="Affected Corridors" value={affected} sub="With expected load" icon={<MapIcon className="h-4 w-4" />} accent="amber" delay={0.18} />
        <KpiCard label="Confidence" value={data.confidence.level} sub={data.confidence.reason} icon={<ShieldCheck className="h-4 w-4" />} accent={data.confidence.level === "HIGH" ? "safe" : "warn"} delay={0.22} />
      </div>

      {/* MAP + RIGHT RAIL */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.8fr_1fr]">
        <Panel title="Live Traffic Overview" icon={<MapIcon className="h-4 w-4" />} action={<LiveTag />} className="flex flex-col" bodyClassName="flex-1 p-3" delay={0.1}>
          <LiveMapView markers={data.top_corridors} height="100%" />
        </Panel>

        <div className="space-y-5">
          <Panel title="Situation Risk" icon={<Activity className="h-4 w-4" />} delay={0.14}>
            <RiskMeter level={data.status} score={data.impact_score} confidence={data.confidence.level} />
            <div className="mt-3 text-center text-xs text-ink-muted">
              Featured event: <span className="font-semibold text-ink">{data.featured.cause}</span> on{" "}
              <span className="font-semibold" style={{ color: RISK_COLOR[data.status] }}>{data.featured.corridor}</span>
            </div>
          </Panel>
          <Panel title="Active Events" icon={<RadioTower className="h-4 w-4" />} delay={0.16}>
            <ActiveEventsPanel events={roster} />
          </Panel>
          <Panel title="Active Alerts" icon={<AlertTriangle className="h-4 w-4" />} delay={0.18}>
            <AlertsPanel alerts={data.alerts} />
          </Panel>
        </div>
      </div>

      {/* BOTTOM ROW */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Panel title="AI Recommended Action Plan" icon={<ListChecks className="h-4 w-4" />} delay={0.2}>
          <ActionPlanCard actions={data.actions} />
        </Panel>
        <Panel title="Top Impacted Corridors" icon={<TrendingUp className="h-4 w-4" />} delay={0.24}>
          <CorridorLoadList corridors={data.top_corridors} />
        </Panel>
        <Panel title="Resource Deployment" icon={<Users className="h-4 w-4" />} delay={0.28}>
          <div className="grid grid-cols-2 gap-3">
            {data.deployment.slice(0, 6).map((d) => (
              <div key={d.corridor} className="rounded-xl border border-line bg-white/[0.03] p-3">
                <div className="text-xs text-ink-muted">{d.corridor}</div>
                <div className="font-display text-2xl font-bold tabular-nums text-brand-bright">{d.officers}</div>
                <div className="text-[10px] uppercase tracking-wide text-ink-faint">{d.role.replace("★ ", "")}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function LiveTag() {
  return (
    <span className="flex items-center gap-1.5 text-[11px] font-semibold text-safe">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping2 rounded-full bg-safe" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-safe" />
      </span>
      LIVE
    </span>
  );
}

