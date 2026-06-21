import { useState } from "react";
import { Map as MapIcon, Radio } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Panel } from "@/components/ui/Panel";
import { LiveMapView } from "@/components/LiveMapView";
import { CorridorLoadList } from "@/components/CorridorLoadList";
import { ErrorState } from "@/components/ui/StateView";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const ANCHOR = new Date("2024-04-15");
const whenFor = (day: string, hour: number) => {
  const d = new Date(ANCHOR);
  d.setDate(d.getDate() + DAYS.indexOf(day));
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}T${String(hour).padStart(2, "0")}:00:00`;
};

export default function LiveMap() {
  const [day, setDay] = useState("Saturday");
  const [hour, setHour] = useState(21);
  const { data, loading, error, reload } = useAsync(() => api.forecast(whenFor(day, hour)), [day, hour]);
  if (error) return <ErrorState msg={error} onRetry={reload} />;
  const corridors = (data?.corridors ?? []).filter((c) => c.expected_load > 0);
  const max = Math.max(...corridors.map((c) => c.expected_load), 0.01);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <MapIcon className="h-6 w-6 text-brand-bright" />
          <div>
            <h1 className="font-display text-2xl font-bold">Live Map</h1>
            <p className="text-sm text-ink-muted">Pan & zoom the city — corridors sized & colored by expected load.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-[11px] font-semibold text-safe">
            <Radio className="h-3.5 w-3.5" /> LIVE
          </span>
          <select value={day} onChange={(e) => setDay(e.target.value)} className="rounded-xl border border-line bg-bg-soft px-3 py-2 text-sm">
            {DAYS.map((d) => <option key={d}>{d}</option>)}
          </select>
          <div className="flex items-center gap-2 rounded-xl border border-line bg-bg-soft px-3 py-2 text-sm">
            <span className="text-ink-muted">Hour</span>
            <input type="range" min={0} max={23} value={hour} onChange={(e) => setHour(+e.target.value)} className="accent-[#3b82f6]" />
            <span className="w-10 tabular-nums">{String(hour).padStart(2, "0")}:00</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_340px]">
        <Panel bodyClassName="p-3">
          <LiveMapView markers={corridors} height={620} />
        </Panel>
        <Panel title="Corridor Load" icon={<MapIcon className="h-4 w-4" />}>
          {loading ? (
            <div className="py-10 text-center text-ink-muted">Loading…</div>
          ) : corridors.length ? (
            <CorridorLoadList corridors={corridors.slice(0, 12)} max={max} />
          ) : (
            <div className="py-10 text-center text-ink-muted">No load for this window.</div>
          )}
        </Panel>
      </div>
    </div>
  );
}
