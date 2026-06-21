import { Bell, Radio } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Panel } from "@/components/ui/Panel";
import { AlertsPanel } from "@/components/AlertsPanel";
import { KpiCard } from "@/components/KpiCard";
import { ErrorState } from "@/components/ui/StateView";

export default function AlertsCenter() {
  const { data, loading, error, reload } = useAsync(() => api.dashboard(), []);
  if (error) return <ErrorState msg={error} onRetry={reload} />;
  if (loading || !data) return <div className="grid h-[50vh] place-items-center text-ink-muted">Loading alerts…</div>;

  const counts = {
    error: data.alerts.filter((a) => a.type === "error").length,
    warning: data.alerts.filter((a) => a.type === "warning").length,
    info: data.alerts.filter((a) => a.type === "info").length,
  };
  const feed = [
    `${new Date().toLocaleTimeString("en-IN", { hour12: false })}  Scenario evaluated for ${data.featured.corridor}`,
    ...data.actions.map((a) => a.replace(/\*\*/g, "")),
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Bell className="h-6 w-6 text-brand-bright" />
        <div>
          <h1 className="font-display text-2xl font-bold">Alerts Center</h1>
          <p className="text-sm text-ink-muted">Active alerts & operational feed for the live scenario.</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <KpiCard label="Critical" value={counts.error} sub="Immediate action" icon={<Bell className="h-4 w-4" />} accent="danger" />
        <KpiCard label="Warnings" value={counts.warning} sub="Prepare resources" icon={<Bell className="h-4 w-4" />} accent="warn" />
        <KpiCard label="Notices" value={counts.info} sub="For awareness" icon={<Bell className="h-4 w-4" />} accent="brand" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel title="Active Alerts" icon={<Bell className="h-4 w-4" />}>
          <AlertsPanel alerts={data.alerts} />
        </Panel>
        <Panel title="Operational Feed" icon={<Radio className="h-4 w-4" />}>
          <ul className="space-y-2">
            {feed.map((f, i) => (
              <li key={i} className="flex items-start gap-2 rounded-lg border border-line bg-white/[0.03] px-3 py-2 text-sm text-ink-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                {f}
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
