import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CorridorLoad } from "@/lib/types";

function color(v: number, max: number) {
  const r = max > 0 ? v / max : 0;
  if (r >= 0.85) return "#ef4444";
  if (r >= 0.6) return "#f97316";
  if (r >= 0.3) return "#eab308";
  return "#22c55e";
}

export function LoadBarChart({ corridors }: { corridors: CorridorLoad[] }) {
  const data = corridors.slice(0, 10);
  const max = Math.max(...data.map((d) => d.expected_load), 0.01);
  return (
    <ResponsiveContainer width="100%" height={Math.max(240, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="corridor"
          width={120}
          tick={{ fill: "#8aa0bd", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{ background: "#0e1626", border: "1px solid rgba(96,165,250,0.2)", borderRadius: 10, color: "#e6edf7" }}
          formatter={(v: number) => [`${v.toFixed(2)} events/3h`, "expected load"]}
        />
        <Bar dataKey="expected_load" radius={[0, 6, 6, 0]} barSize={16}>
          {data.map((d, i) => (
            <Cell key={i} fill={color(d.expected_load, max)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
