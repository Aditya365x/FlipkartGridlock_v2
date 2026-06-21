import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Users, Construction, Route, Ambulance, FlaskConical, RefreshCw, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useScenario } from "@/lib/scenario";
import type { ActionPlan } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { KpiCard } from "@/components/KpiCard";
import { ActionPlanCard } from "@/components/ActionPlanCard";
import { fmtDur, RISK_COLOR } from "@/lib/format";

export default function ResourcePlanner() {
  const { scenario, setScenario } = useScenario();

  // ---- empty state: nothing planned yet ----
  if (!scenario) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <div className="glass flex max-w-md flex-col items-center gap-3 px-10 py-12 text-center">
          <FlaskConical className="h-10 w-10 text-brand-bright" />
          <div className="font-display text-xl font-bold">No event planned yet</div>
          <p className="text-sm text-ink-muted">
            The Resource Planner deploys for the event you simulate. Plan one first, then come back —
            the officers, barricades and diversions will be tailored to it.
          </p>
          <Link to="/simulation" className="mt-2 rounded-xl bg-gradient-to-r from-brand to-brand-cyan px-4 py-2.5 font-semibold text-white shadow-glow hover:brightness-110">
            Go to Event Planner →
          </Link>
        </div>
      </div>
    );
  }

  return <Planner key={scenario.input.corridor + scenario.input.when} scenario={scenario} setScenario={setScenario} />;
}

function Planner({ scenario, setScenario }: { scenario: NonNullable<ReturnType<typeof useScenario>["scenario"]>; setScenario: ReturnType<typeof useScenario>["setScenario"] }) {
  const [officers, setOfficers] = useState(scenario.input.total_officers);
  const [plan, setPlan] = useState<ActionPlan>(scenario.result);
  const [busy, setBusy] = useState(false);

  // re-deploy when the officer pool changes (debounced)
  useEffect(() => {
    if (officers === scenario.input.total_officers) return;
    const t = setTimeout(async () => {
      setBusy(true);
      try {
        const res = await api.actionPlan({ ...scenario.input, total_officers: officers });
        setPlan(res);
        setScenario({ input: { ...scenario.input, total_officers: officers }, result: res });
      } finally {
        setBusy(false);
      }
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [officers]);

  const d = plan.decision;
  const actions = d.actions;
  const barricades = actions.filter((a) => /barricade/i.test(a)).length;
  const diversions = actions.filter((a) => /diversion|route/i.test(a)).length;
  const units = actions.filter((a) => /emergency|ambulance|tow/i.test(a)).length;
  const riskColor = RISK_COLOR[d.risk.level];

  // The "diversion playbook" — real historical closures on this corridor (no synthetic routes).
  const playbook = useAsync(
    () => api.closures(scenario.input.corridor, scenario.input.event_cause),
    [scenario.input.corridor, scenario.input.event_cause],
  );
  const closures = playbook.data?.recent_closures ?? [];

  return (
    <div className="space-y-5">
      {/* scenario header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-brand-bright" />
          <div>
            <h1 className="font-display text-2xl font-bold">Resource Planner</h1>
            <p className="text-sm text-ink-muted">
              Deployment for your planned event ·{" "}
              <span className="font-semibold text-ink">{scenario.input.event_cause}</span> on{" "}
              <span className="font-semibold" style={{ color: riskColor }}>{scenario.input.corridor}</span>
              {scenario.input.day && ` · ${scenario.input.day} ${String(scenario.input.hour).padStart(2, "0")}:00`}
            </p>
          </div>
        </div>
        <span className="rounded-full px-4 py-1.5 text-sm font-bold" style={{ color: riskColor, background: `${riskColor}1f` }}>
          {d.risk.icon} {d.risk.level} RISK
        </span>
      </div>

      {/* officer pool control */}
      <Panel>
        <div className="flex flex-wrap items-center gap-4">
          <div className="min-w-[220px] flex-1">
            <div className="flex items-center justify-between">
              <span className="panel-title">Available officers (city-wide)</span>
              <span className="font-display text-lg font-bold tabular-nums text-brand-bright">{officers}</span>
            </div>
            <input type="range" min={5} max={200} value={officers} onChange={(e) => setOfficers(+e.target.value)} className="mt-2 w-full accent-[#3b82f6]" />
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            {busy ? <><RefreshCw className="h-4 w-4 animate-spin" /> Re-optimizing…</> : <>Drag to re-run the deployment optimizer live.</>}
          </div>
        </div>
      </Panel>

      {/* resource KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Officers (event corridor)" value={`${plan.officers_event}/${officers}`} sub="Sized by predicted impact" icon={<Users className="h-4 w-4" />} accent="brand" />
        <KpiCard label="Barricades" value={barricades ? "REQUIRED" : "—"} sub={`Closure ${Math.round(plan.prediction.road_closure_prob * 100)}%`} icon={<Construction className="h-4 w-4" />} accent={barricades ? "warn" : "safe"} />
        <KpiCard label="Diversion Playbook" value={diversions ? closures.length : "—"} sub={diversions ? "Historical closure references" : "Not required"} icon={<Route className="h-4 w-4" />} accent="brand" />
        <KpiCard label="Emergency Units" value={units} sub={units ? "On standby" : "Not required"} icon={<Ambulance className="h-4 w-4" />} accent={units ? "danger" : "safe"} />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1fr]">
        <Panel title="Officer Allocation by Corridor" icon={<Users className="h-4 w-4" />}>
          <div className="space-y-2">
            {plan.deployment.map((row) => {
              const isEvent = row.role.includes("EVENT");
              return (
                <div key={row.corridor} className={`flex items-center justify-between rounded-xl border px-3 py-2.5 ${isEvent ? "border-brand/40 bg-brand/10" : "border-line bg-white/[0.03]"}`}>
                  <div>
                    <div className="text-sm font-semibold text-ink">{isEvent ? "★ " : ""}{row.corridor}</div>
                    <div className="text-[10px] uppercase tracking-wide text-ink-faint">{row.role.replace("★ ", "")}</div>
                  </div>
                  <div className="font-display text-2xl font-bold tabular-nums text-brand-bright">{row.officers}</div>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-ink-faint">
            The event corridor is staffed by predicted impact ({fmtDur(plan.prediction.expected_duration_min)} window);
            the rest is spread by the <Link to="/forecast" className="text-brand-bright underline">expected corridor load</Link> so the city keeps cover.
          </p>
        </Panel>
        <Panel title="Recommended Actions" icon={<Construction className="h-4 w-4" />}>
          <ActionPlanCard actions={actions} />
        </Panel>
      </div>

      {/* Diversion playbook — only meaningful when a closure/diversion is recommended */}
      {diversions > 0 && (
        <Panel title="Diversion Playbook — Historical Closures on this Corridor" icon={<Route className="h-4 w-4" />}>
          <p className="mb-3 text-xs text-ink-faint">
            This dataset has no route/direction data, so we don't fabricate turn-by-turn diversions.
            Instead we surface <span className="text-ink-muted">real past closures</span> on{" "}
            <span className="font-semibold text-ink">{scenario.input.corridor}</span> (closest cause first) —
            a reference for how similar disruptions were handled.
          </p>
          {playbook.loading ? (
            <div className="py-6 text-center text-sm text-ink-muted">Loading playbook…</div>
          ) : closures.length === 0 ? (
            <div className="py-6 text-center text-sm text-ink-muted">No historical closures recorded for this corridor.</div>
          ) : (
            <div className="space-y-2">
              {closures.map((c, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl border border-line bg-white/[0.03] px-3 py-2.5">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-brand-cyan" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-ink">{c.address ?? "—"}</div>
                    <div className="text-[11px] text-ink-faint">
                      {c.date ?? "—"}{c.event_cause ? ` · ${c.event_cause}` : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}
