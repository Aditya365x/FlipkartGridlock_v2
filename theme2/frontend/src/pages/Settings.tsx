import { Settings as Cog, Cpu, ShieldCheck, Database } from "lucide-react";
import { Panel } from "@/components/ui/Panel";

const MODELS = [
  ["Road-closure classifier", "LightGBM + isotonic calibration", "PR-AUC 0.32 · recall 0.58 @ thr 0.14"],
  ["Impact-duration regressor", "LightGBM (log-target, artifact-filtered)", "MAE 117 min"],
  ["Severity / priority", "Operational rule (named corridor → High)", "rule-based"],
  ["Hotspot load forecaster", "LightGBM (typical-load)", "MAE 0.40 · P@10 0.51"],
];

export default function Settings() {
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Cog className="h-6 w-6 text-brand-bright" />
        <div>
          <h1 className="font-display text-2xl font-bold">Settings</h1>
          <p className="text-sm text-ink-muted">System configuration & model registry.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel title="Operational Defaults" icon={<ShieldCheck className="h-4 w-4" />}>
          <div className="space-y-3 text-sm">
            <Row label="City-wide officer pool" value="30" />
            <Row label="Event-corridor reserve cap" value="75%" />
            <Row label="Closure decision threshold" value="0.14 (recall-leaning)" />
            <Row label="Min officers / covered corridor" value="1" />
            <Row label="Timezone" value="Asia/Kolkata (IST)" />
          </div>
        </Panel>
        <Panel title="Data Source" icon={<Database className="h-4 w-4" />}>
          <div className="space-y-3 text-sm">
            <Row label="Dataset" value="ASTraM event log" />
            <Row label="Events" value="8,173" />
            <Row label="Window" value="Nov 2023 – Apr 2024" />
            <Row label="Live feed" value="Not connected (roadmap)" warn />
          </div>
        </Panel>
      </div>

      <Panel title="Model Registry" icon={<Cpu className="h-4 w-4" />}>
        <div className="overflow-hidden rounded-xl border border-line">
          {MODELS.map(([name, kind, metric], i) => (
            <div key={name} className={`grid grid-cols-3 gap-2 px-4 py-3 text-sm ${i % 2 ? "bg-white/[0.02]" : ""}`}>
              <div className="font-semibold text-ink">{name}</div>
              <div className="text-ink-muted">{kind}</div>
              <div className="text-right tabular-nums text-brand-bright">{metric}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function Row({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-line bg-white/[0.03] px-3 py-2.5">
      <span className="text-ink-muted">{label}</span>
      <span className={warn ? "font-semibold text-warn" : "font-semibold text-ink"}>{value}</span>
    </div>
  );
}
