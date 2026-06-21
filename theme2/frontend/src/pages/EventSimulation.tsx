import { useState } from "react";
import { FlaskConical, Play, Construction, Clock, Gauge, ShieldCheck, ListChecks, Users, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { useScenario } from "@/lib/scenario";
import type { ActionPlan, EventInput } from "@/lib/types";
import { fmtDur, pct } from "@/lib/format";
import { Panel } from "@/components/ui/Panel";
import { RiskMeter } from "@/components/RiskMeter";
import { ActionPlanCard } from "@/components/ActionPlanCard";
import { AlertsPanel } from "@/components/AlertsPanel";
import { KpiCard } from "@/components/KpiCard";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const ANCHOR = new Date("2024-04-15"); // a Monday, matching the backend's shared time axis

function whenFor(day: string, hour: number) {
  const d = new Date(ANCHOR);
  d.setDate(d.getDate() + DAYS.indexOf(day));
  d.setHours(hour, 0, 0, 0);
  // local ISO without timezone suffix (backend treats wall-clock as Bengaluru-local)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}T${String(hour).padStart(2, "0")}:00:00`;
}

// Three contrasting demo scenarios (numbers verified against the live model).
const DEMO_CASES = [
  {
    key: "accident",
    label: "🚗 Accident",
    tag: "Contained incident · MEDIUM",
    accent: "#22c55e",
    input: { event_type: "unplanned", event_cause: "accident", corridor: "CBD 2", zone: "Central Zone 1", day: "Tuesday", hour: 14, total_officers: 30 },
  },
  {
    key: "rally",
    label: "📢 Political Rally",
    tag: "Closure + barricades · HIGH",
    accent: "#f97316",
    input: { event_type: "unplanned", event_cause: "protest", corridor: "Bellary Road 1", zone: "unknown", day: "Saturday", hour: 12, total_officers: 40 },
  },
  {
    key: "festival",
    label: "🎉 Festival",
    tag: "Large-scale planning · CRITICAL",
    accent: "#ef4444",
    input: { event_type: "planned", event_cause: "public_event", corridor: "Mysore Road", zone: "unknown", day: "Sunday", hour: 18, total_officers: 60 },
  },
] as const;

export default function EventSimulation() {
  const meta = useAsync(() => api.meta(), []);
  const { scenario, setScenario } = useScenario();
  // restore the last planned scenario when returning to this page (state otherwise resets on nav)
  const [form, setForm] = useState<EventInput & { day: string; hour: number }>(() =>
    scenario
      ? {
          event_type: scenario.input.event_type,
          event_cause: scenario.input.event_cause,
          corridor: scenario.input.corridor,
          zone: scenario.input.zone,
          day: scenario.input.day ?? "Monday",
          hour: scenario.input.hour ?? 19,
          total_officers: scenario.input.total_officers,
        }
      : {
          event_type: "planned",
          event_cause: "public_event",
          corridor: "CBD 2",
          zone: "Central Zone 1",
          day: "Monday",
          hour: 19,
          total_officers: 30,
        },
  );
  const [result, setResult] = useState<ActionPlan | null>(scenario?.result ?? null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [logging, setLogging] = useState(false);
  const [logMsg, setLogMsg] = useState<string | null>(null);

  async function logForReview() {
    if (!result) return;
    setLogging(true);
    setLogMsg(null);
    try {
      const input = {
        event_type: form.event_type,
        event_cause: form.event_cause,
        corridor: form.corridor,
        zone: form.zone,
        when: whenFor(form.day, form.hour),
        total_officers: form.total_officers ?? 30,
      };
      const res = await api.learningLog(input);
      setLogMsg(`Logged ✓ (id ${res.logged_id}). It's now pending in Post-Event Learning — record the real outcome there after the event.`);
    } catch (e: any) {
      setLogMsg(`Failed to log: ${String(e?.message ?? e)}`);
    } finally {
      setLogging(false);
    }
  }

  async function submit(f: typeof form) {
    setBusy(true);
    setErr(null);
    try {
      const input = {
        event_type: f.event_type,
        event_cause: f.event_cause,
        corridor: f.corridor,
        zone: f.zone,
        when: whenFor(f.day, f.hour),
        total_officers: f.total_officers ?? 30,
      };
      const res = await api.actionPlan(input);
      setResult(res);
      // publish so the Resource Planner deploys for THIS event, not a static default
      setScenario({ input: { ...input, day: f.day, hour: f.hour }, result: res });
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }
  const run = () => submit(form);

  function loadCase(c: (typeof DEMO_CASES)[number]) {
    const f = { ...form, ...c.input };
    setForm(f);
    submit(f);
  }

  const m = meta.data;
  const sel = (label: string, key: keyof typeof form, opts: string[]) => (
    <label className="block">
      <span className="panel-title">{label}</span>
      <select
        value={form[key] as string}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="mt-1 w-full rounded-xl border border-line bg-bg-soft px-3 py-2.5 text-sm text-ink outline-none focus:border-brand/50"
      >
        {opts.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-6 w-6 text-brand-bright" />
          <div>
            <h1 className="font-display text-2xl font-bold">Event Simulation</h1>
            <p className="text-sm text-ink-muted">Model an event's impact and get a deployment plan before it happens.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="self-center text-[11px] uppercase tracking-wider text-ink-faint">Demo cases:</span>
          {DEMO_CASES.map((c) => (
            <button
              key={c.key}
              onClick={() => loadCase(c)}
              disabled={busy}
              className="group rounded-xl border px-3 py-2 text-left transition hover:brightness-110 disabled:opacity-60"
              style={{ borderColor: `${c.accent}55`, background: `${c.accent}14` }}
            >
              <div className="text-sm font-semibold" style={{ color: c.accent }}>{c.label}</div>
              <div className="text-[10px] text-ink-muted">{c.tag}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[380px_1fr]">
        {/* INPUTS */}
        <Panel title="Scenario Inputs" icon={<Gauge className="h-4 w-4" />}>
          <div className="space-y-3">
            {sel("Event type", "event_type", m?.event_type ?? ["planned", "unplanned"])}
            {sel("Event cause", "event_cause", m?.event_cause ?? ["public_event"])}
            {sel("Corridor", "corridor", m?.corridor ?? ["CBD 2"])}
            {sel("Zone", "zone", m?.zone ?? ["Central Zone 1"])}
            <div className="grid grid-cols-2 gap-3">
              {sel("Day", "day", DAYS)}
              <label className="block">
                <span className="panel-title">Hour: {String(form.hour).padStart(2, "0")}:00</span>
                <input type="range" min={0} max={23} value={form.hour} onChange={(e) => setForm({ ...form, hour: +e.target.value })} className="mt-3 w-full accent-[#3b82f6]" />
              </label>
            </div>
            <label className="block">
              <span className="panel-title">Available officers (city-wide): {form.total_officers}</span>
              <input type="range" min={5} max={200} value={form.total_officers} onChange={(e) => setForm({ ...form, total_officers: +e.target.value })} className="mt-3 w-full accent-[#3b82f6]" />
            </label>
            <button
              onClick={run}
              disabled={busy}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand to-brand-cyan py-3 font-semibold text-white shadow-glow transition hover:brightness-110 disabled:opacity-60"
            >
              <Play className="h-4 w-4" /> {busy ? "Simulating…" : "Run Simulation"}
            </button>
            {err && <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">{err}</div>}
          </div>
        </Panel>

        {/* OUTPUTS */}
        <div className="space-y-5">
          {!result ? (
            <Panel><div className="grid h-[360px] place-items-center text-ink-muted">Run a simulation to see the predicted impact and action plan.</div></Panel>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <KpiCard label="Road-closure" value={pct(result.prediction.road_closure_prob)} sub={result.prediction.needs_barricade ? "Barricade recommended" : "No closure"} icon={<Construction className="h-4 w-4" />} accent={result.prediction.needs_barricade ? "warn" : "brand"} />
                <KpiCard label="Impact duration" value={fmtDur(result.prediction.expected_duration_min)} sub="Disruption window" icon={<Clock className="h-4 w-4" />} accent="brand" />
                <KpiCard label="Officers (event)" value={result.officers_event} sub="To event corridor" icon={<Users className="h-4 w-4" />} accent="brand" />
                <KpiCard label="Confidence" value={result.prediction.confidence.toUpperCase()} sub={result.prediction.out_of_distribution ? "Out-of-distribution" : "In-distribution"} icon={<ShieldCheck className="h-4 w-4" />} accent={result.prediction.confidence === "high" ? "safe" : "warn"} />
              </div>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr]">
                <Panel title="Risk Assessment"><RiskMeter level={result.decision.risk.level} score={result.decision.risk.score} confidence={result.decision.confidence.level} /></Panel>
                <Panel title="AI Recommended Action Plan" icon={<ListChecks className="h-4 w-4" />}>
                  {result.decision.alerts.length > 0 && <div className="mb-3"><AlertsPanel alerts={result.decision.alerts} /></div>}
                  <ActionPlanCard actions={result.decision.actions} />
                </Panel>
              </div>

              {/* log this prediction into the post-event learning loop */}
              <Panel>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm text-ink-muted">
                    Logging keeps this prediction on record. After the real event, enter what actually
                    happened in <b className="text-ink">Post-Event Learning</b> so the model learns from it.
                  </div>
                  <button
                    onClick={logForReview}
                    disabled={logging}
                    className="flex shrink-0 items-center gap-2 rounded-xl border border-brand/40 bg-brand/10 px-4 py-2.5 text-sm font-semibold text-brand-bright hover:bg-brand/20 disabled:opacity-60"
                  >
                    <Save className="h-4 w-4" /> {logging ? "Logging…" : "📝 Log for post-event review"}
                  </button>
                </div>
                {logMsg && <div className="mt-3 rounded-lg border border-safe/40 bg-safe/10 px-3 py-2 text-xs text-safe">{logMsg}</div>}
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
