import { FileText, Download } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Panel } from "@/components/ui/Panel";
import { ErrorState } from "@/components/ui/StateView";
import { fmtDur, pct } from "@/lib/format";

export default function Reports() {
  const { data, loading, error, reload } = useAsync(() => api.dashboard(), []);
  if (error) return <ErrorState msg={error} onRetry={reload} />;
  if (loading || !data) return <div className="grid h-[50vh] place-items-center text-ink-muted">Generating report…</div>;

  const download = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `event-shield-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const rows: [string, string][] = [
    ["Featured corridor", data.featured.corridor],
    ["Event cause", data.featured.cause],
    ["Overall risk", `${data.status} (${data.impact_score.toFixed(0)}/100)`],
    ["Road-closure probability", pct(data.closure_prob)],
    ["Barricade recommended", data.needs_barricade ? "Yes" : "No"],
    ["Expected impact window", fmtDur(data.expected_impact_min)],
    ["Officers (event corridor)", `${data.officers.deployed} of ${data.officers.total}`],
    ["Prediction confidence", data.confidence.level],
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-brand-bright" />
          <div>
            <h1 className="font-display text-2xl font-bold">Reports</h1>
            <p className="text-sm text-ink-muted">Current situation report — export for the control room log.</p>
          </div>
        </div>
        <button onClick={download} className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand to-brand-cyan px-4 py-2.5 font-semibold text-white shadow-glow hover:brightness-110">
          <Download className="h-4 w-4" /> Export JSON
        </button>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel title="Situation Summary">
          <dl className="divide-y divide-line">
            {rows.map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-2.5 text-sm">
                <dt className="text-ink-muted">{k}</dt>
                <dd className="font-semibold text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel title="Recommended Actions (logged)">
          <ol className="space-y-2">
            {data.actions.map((a, i) => (
              <li key={i} className="rounded-lg border border-line bg-white/[0.03] px-3 py-2 text-sm text-ink">
                {i + 1}. {a.replace(/\*\*/g, "")}
              </li>
            ))}
          </ol>
        </Panel>
      </div>
    </div>
  );
}
