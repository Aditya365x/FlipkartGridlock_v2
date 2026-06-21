import { createContext, useContext, useState, type ReactNode } from "react";
import type { ActionPlan, EventInput } from "./types";

export interface Scenario {
  input: Required<Pick<EventInput, "event_type" | "event_cause" | "corridor" | "zone">> & {
    when: string;
    total_officers: number;
    day?: string;
    hour?: number;
  };
  result: ActionPlan;
}

interface Ctx {
  scenario: Scenario | null;
  setScenario: (s: Scenario | null) => void;
}

const ScenarioContext = createContext<Ctx>({ scenario: null, setScenario: () => {} });

/** Shares the planned event across Event Planner -> Resource Planner (and beyond). */
export function ScenarioProvider({ children }: { children: ReactNode }) {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  return <ScenarioContext.Provider value={{ scenario, setScenario }}>{children}</ScenarioContext.Provider>;
}

export const useScenario = () => useContext(ScenarioContext);
