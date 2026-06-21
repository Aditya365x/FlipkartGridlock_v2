import { useState } from "react";
import { Brain, Target, Timer, Repeat, Sprout, Trash2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import type { LearningLogRow } from "@/lib/types";
import { Panel } from "@/components/ui/Panel";
import { KpiCard } from "@/components/KpiCard";
import { ErrorState, Loading } from "@/components/ui/StateView";
import { fmtDur } from "@/lib/format";

export default function PostEventAnalytics() {
  const { data, loading, error, reload } = useAsync(() => api.learning(), []);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      await fn();
      reload();
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorState msg={error} onRetry={reload} />;
  if (loading || !data) return <Loading label="Loading learning loop…" />;

  const { metrics: m, calibration: c, log } = data;
  const pending = log.filter((r) => !r.resolved);
  const maeRaw = m.duration_mae_raw;
  const maeCal = m.duration_mae_calibrated;
  const maeMax = Math.max(maeRaw ?? 0, maeCal ?? 0, 1);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Brain className="h-6 w-6 text-brand-bright" />
          <div>
            <h1 className="font-display text-2xl font-bold">Post-Event Learning</h1>
            <p className="text-sm text-ink-muted">Predict → log → record actuals → recalibrate. Live, backed by the model.</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => run(() => api.learningSeed(30))} disabled={busy}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand to-brand-cyan px-4 py-2.5 text-sm font-semibold text-white shadow-glow hover:brightness-110 disabled:opacity-60">
            {busy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sprout className="h-4 w-4" />} Seed 30 real events
          </button>
          <button onClick={() => run(() => api.learningClear())} disabled={busy}
            className="flex items-center gap-2 rounded-xl border border-line bg-white/5 px-3 py-2.5 text-sm text-ink-muted hover:border-danger/40 hover:text-danger disabled:opacity-60">
            <Trash2 className="h-4 w-4" /> Clear
          </button>
        </div>
      </div>

      {m.n_logged === 0 ? (
        <Panel>
          <div className="grid h-[300px] place-items-center text-center">
            <div>
              <Sprout className="mx-auto mb-3 h-10 w-10 text-brand-bright" />
              <div className="font-display text-lg font-bold">The loop is empty</div>
              <p className="mx-auto mt-1 max-w-md text-sm text-ink-muted">
                Click <b>Seed 30 real events</b> — it predicts 30 real historical events, records their true
                outcomes, and learns a calibration. Then watch the metrics and calibration update live.
              </p>
            </div>
          </div>
        </Panel>
      ) : (
        <>
          {/* live scoreboard */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard label="Reviewed Events" value={m.n_resolved} sub={`${m.n_logged} logged`} icon={<Repeat className="h-4 w-4" />} accent="brand" />
            <KpiCard label="Closure Accuracy" value={m.closure_accuracy == null ? "—" : `${Math.round(m.closure_accuracy * 100)}%`} sub="Predicted vs actual" icon={<Target className="h-4 w-4" />} accent="safe" />
            <KpiCard label="Clearance MAE (raw)" value={maeRaw == null ? "—" : `${maeRaw.toFixed(0)}m`} sub="Before calibration" icon={<Timer className="h-4 w-4" />} accent="amber" />
            <KpiCard label="Clearance MAE (calibrated)" value={maeCal == null ? "—" : `${maeCal.toFixed(0)}m`}
              sub={maeRaw != null && maeCal != null ? `${(maeCal - maeRaw).toFixed(0)}m vs raw` : "After learning"} icon={<Timer className="h-4 w-4" />} accent="safe" />
          </div>

          {/* what it learned */}
          <Panel title="What the loop has learned (live)">
            {c.active ? (
              <div className="rounded-xl border border-safe/40 bg-safe/10 px-4 py-3 text-sm text-ink">
                ✅ Calibration <b>active</b> from <b>{c.n_resolved}</b> reviewed events. Future predictions auto-adjust:
                clearance ×<b>{c.duration_factor.toFixed(2)}</b>, closure probability <b>{(c.closure_prob_shift * 100).toFixed(0)}%</b>.
                {c.updated_at && <span className="text-ink-faint"> · updated {new Date(c.updated_at).toLocaleTimeString("en-IN", { hour12: false })}</span>}
              </div>
            ) : (
              <div className="rounded-xl border border-warn/40 bg-warn/10 px-4 py-3 text-sm text-ink">
                Calibration inactive — needs ≥5 reviewed events (have {m.n_resolved}). Record outcomes below to activate it.
              </div>
            )}
          </Panel>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {/* the loop */}
            <Panel title="The Learning Loop">
              <ol className="space-y-3">
                {[
                  ["Predict", "Model forecasts closure, impact & risk for an event."],
                  ["Log", "The prediction is saved to the feedback log."],
                  ["Record actuals", "After the event, the real outcome is entered (below)."],
                  ["Recalibrate", "Isotonic calibration + duration factor update automatically."],
                  ["Improve", "Future predictions across all modules get sharper."],
                ].map(([t, d], i) => (
                  <li key={t} className="flex gap-3">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand/20 text-sm font-bold text-brand-bright">{i + 1}</span>
                    <div>
                      <div className="font-semibold text-ink">{t}</div>
                      <div className="text-sm text-ink-muted">{d}</div>
                    </div>
                  </li>
                ))}
              </ol>
            </Panel>

            {/* calibration impact (live) */}
            <Panel title="Calibration Impact (live)">
              {maeRaw == null ? (
                <div className="py-8 text-center text-sm text-ink-muted">Record clearance outcomes to see the effect.</div>
              ) : (
                <div className="space-y-4 py-2">
                  <Bar label="Clearance MAE — raw model" value={maeRaw} max={maeMax} color="#f97316" suffix="m" />
                  <Bar label="Clearance MAE — calibrated" value={maeCal ?? maeRaw} max={maeMax} color="#22c55e" suffix="m" />
                  {m.closure_accuracy != null && <Bar label="Closure-call accuracy" value={Math.round(m.closure_accuracy * 100)} max={100} color="#3b82f6" suffix="%" />}
                </div>
              )}
              <p className="mt-3 text-xs text-ink-faint">These numbers are computed live from the feedback log — seed or record outcomes and they change.</p>
            </Panel>
          </div>

          {/* record actuals */}
          <RecordPanel pending={pending} busy={busy} onRecord={(b) => run(() => api.learningRecord(b))} />
        </>
      )}
    </div>
  );
}

function RecordPanel({ pending, busy, onRecord }: {
  pending: LearningLogRow[];
  busy: boolean;
  onRecord: (b: { id: string; actual_closure: boolean; actual_duration_min: number; actual_high_priority: boolean }) => void;
}) {
  const [id, setId] = useState("");
  const [closure, setClosure] = useState("no");
  const [dur, setDur] = useState(60);
  const [high, setHigh] = useState("no");
  const sel = id || pending[0]?.id || "";

  return (
    <Panel title="Record What Actually Happened">
      {pending.length === 0 ? (
        <div className="py-6 text-center text-sm text-ink-muted">No predictions awaiting review. ✅ (Seed more to continue.)</div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr_1fr_1fr_auto] md:items-end">
          <label className="block">
            <span className="panel-title">Pending prediction</span>
            <select value={sel} onChange={(e) => setId(e.target.value)} className="mt-1 w-full rounded-xl border border-line bg-bg-soft px-3 py-2.5 text-sm">
              {pending.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.corridor} · {p.event_cause} · pred {p.pred_closure_prob != null ? `${Math.round(p.pred_closure_prob * 100)}%` : "—"} / {fmtDur(p.pred_duration_min ?? 0)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="panel-title">Needed closure?</span>
            <select value={closure} onChange={(e) => setClosure(e.target.value)} className="mt-1 w-full rounded-xl border border-line bg-bg-soft px-3 py-2.5 text-sm">
              <option value="yes">yes</option><option value="no">no</option>
            </select>
          </label>
          <label className="block">
            <span className="panel-title">Actual clearance (min)</span>
            <input type="number" min={0} max={2880} value={dur} onChange={(e) => setDur(+e.target.value)} className="mt-1 w-full rounded-xl border border-line bg-bg-soft px-3 py-2.5 text-sm" />
          </label>
          <label className="block">
            <span className="panel-title">High priority?</span>
            <select value={high} onChange={(e) => setHigh(e.target.value)} className="mt-1 w-full rounded-xl border border-line bg-bg-soft px-3 py-2.5 text-sm">
              <option value="yes">yes</option><option value="no">no</option>
            </select>
          </label>
          <button
            onClick={() => onRecord({ id: sel, actual_closure: closure === "yes", actual_duration_min: dur, actual_high_priority: high === "yes" })}
            disabled={busy || !sel}
            className="rounded-xl bg-gradient-to-r from-brand to-brand-cyan px-4 py-2.5 text-sm font-semibold text-white shadow-glow hover:brightness-110 disabled:opacity-60">
            Save &amp; learn
          </button>
        </div>
      )}
    </Panel>
  );
}

function Bar({ label, value, max, color, suffix }: { label: string; value: number; max: number; color: string; suffix: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-ink-muted">{label}</span>
        <span className="tabular-nums" style={{ color }}>{value.toFixed(0)}{suffix}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/5">
        <div className="h-full rounded-full" style={{ width: `${(value / max) * 100}%`, backgroundColor: color, boxShadow: `0 0 10px ${color}` }} />
      </div>
    </div>
  );
}
