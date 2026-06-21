// Types mirror the FastAPI responses in api/main.py.

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AlertType = "error" | "warning" | "info";

export interface Prediction {
  severity_high_prob: number;
  predicted_priority: "High" | "Low";
  road_closure_prob: number;
  needs_barricade: boolean;
  closure_threshold: number;
  expected_duration_min: number;
  confidence: "high" | "low";
  out_of_distribution: boolean;
  warnings: string[];
  calibrated?: boolean;
}

export interface Risk {
  level: RiskLevel;
  icon: string;
  color: string;
  score: number;
}

export interface Confidence {
  level: string;
  reason: string;
}

export interface Alert {
  type: AlertType;
  msg: string;
}

export interface DecisionBrief {
  risk: Risk;
  confidence: Confidence;
  expected_impact_min: number;
  alerts: Alert[];
  actions: string[];
}

export interface DeploymentRow {
  corridor: string;
  officers: number;
  demand_weight: number;
  role: string;
}

export interface CorridorLoad {
  corridor: string;
  expected_load: number;
  lat?: number;
  lon?: number;
}

export interface ActiveEvent {
  corridor: string;
  cause: string;
  event_type: string;
  expected_load: number;
  risk: RiskLevel;
  score: number;
  closure_prob: number;
  needs_barricade: boolean;
  impact_min: number;
  lat?: number;
  lon?: number;
  planned?: boolean; // true when this row is the user's planned event (from Event Planner)
}

export interface DashboardData {
  simulated: boolean;
  generated_at: string;
  active_events: ActiveEvent[];
  featured: { corridor: string; cause: string };
  status: RiskLevel;
  impact_score: number;
  closure_prob: number;
  needs_barricade: boolean;
  expected_impact_min: number;
  confidence: Confidence;
  officers: { deployed: number; total: number };
  alerts: Alert[];
  actions: string[];
  deployment: DeploymentRow[];
  top_corridors: CorridorLoad[];
}

export interface ActionPlan {
  prediction: Prediction;
  decision: DecisionBrief;
  officers_event: number;
  deployment: DeploymentRow[];
}

export interface Meta {
  event_type: string[];
  event_cause: string[];
  corridor: string[];
  zone: string[];
}

export interface LearningMetrics {
  n_logged: number;
  n_resolved: number;
  closure_accuracy: number | null;
  duration_mae_raw: number | null;
  duration_mae_calibrated: number | null;
  priority_accuracy: number | null;
}

export interface Calibration {
  n_resolved: number;
  duration_factor: number;
  closure_prob_shift: number;
  active: boolean;
  updated_at?: string;
}

export interface LearningLogRow {
  id: string;
  corridor: string;
  event_cause: string;
  pred_closure_prob: number | null;
  pred_duration_min: number | null;
  resolved: boolean;
  actual_closure: boolean | null;
  actual_duration_min: number | null;
}

export interface LearningData {
  metrics: LearningMetrics;
  calibration: Calibration;
  log: LearningLogRow[];
}

export interface EventInput {
  event_type: string;
  event_cause: string;
  corridor: string;
  zone: string;
  when?: string | null;
  total_officers?: number;
}
