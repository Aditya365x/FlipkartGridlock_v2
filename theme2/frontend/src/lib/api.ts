import type { ActionPlan, DashboardData, EventInput, LearningData, Meta } from "./types";

// In dev, Vite proxies /api -> http://127.0.0.1:8000 (see vite.config.ts).
// Override with VITE_API_URL for production.
const BASE = import.meta.env.VITE_API_URL ?? "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error((detail as any)?.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string }>("/health"),
  meta: () => req<Meta>("/meta"),
  dashboard: (when?: string) => req<DashboardData>(`/dashboard${when ? `?when=${encodeURIComponent(when)}` : ""}`),
  forecast: (when?: string | null) =>
    req<{ when: string | null; corridors: { corridor: string; expected_load: number }[] }>("/forecast", {
      method: "POST",
      body: JSON.stringify({ when }),
    }),
  actionPlan: (ev: EventInput) =>
    req<ActionPlan>("/action_plan", { method: "POST", body: JSON.stringify(ev) }),
  closures: (corridor: string, cause?: string) =>
    req<{ corridor: string; recent_closures: { date?: string; address?: string; event_cause?: string }[] }>(
      `/corridor_closures/${encodeURIComponent(corridor)}${cause ? `?event_cause=${encodeURIComponent(cause)}` : ""}`,
    ),
  // post-event learning loop (live, backed by feedback.py)
  learning: () => req<LearningData>("/learning"),
  learningLog: (ev: EventInput) => req<LearningData & { logged_id?: string }>("/learning/log", { method: "POST", body: JSON.stringify(ev) }),
  learningSeed: (n = 30) => req<LearningData>(`/learning/seed?n=${n}`, { method: "POST" }),
  learningRecord: (body: { id: string; actual_closure: boolean; actual_duration_min: number; actual_high_priority: boolean }) =>
    req<LearningData>("/learning/record", { method: "POST", body: JSON.stringify(body) }),
  learningClear: () => req<LearningData>("/learning/clear", { method: "POST" }),
};
