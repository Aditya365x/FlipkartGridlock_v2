import { createContext, useContext, useEffect, type ReactNode } from "react";
import { api } from "./api";
import { useAsync } from "./useAsync";
import type { DashboardData } from "./types";

interface Ctx {
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const DashboardContext = createContext<Ctx>({ data: null, loading: true, error: null, reload: () => {} });

/**
 * Single source of truth for the live dashboard — shared by the top alert banner and the
 * Command Center so they never disagree, and polled in ONE place (no duplicate fetches).
 */
export function DashboardProvider({ children }: { children: ReactNode }) {
  const state = useAsync(() => api.dashboard(), []);
  useEffect(() => {
    const t = setInterval(state.reload, 20000);
    return () => clearInterval(t);
  }, [state.reload]);
  return <DashboardContext.Provider value={state}>{children}</DashboardContext.Provider>;
}

export const useDashboard = () => useContext(DashboardContext);
