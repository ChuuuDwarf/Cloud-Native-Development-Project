// Generated to mirror backend/app/modules/dashboard/schemas.py.
// Keep these two in sync — backend uses snake_case on the wire (no aliases),
// so frontend mirrors snake_case 1:1.

import type { Severity } from "@/constants/enums";
import type { MachineStatus } from "./machines";
import type { WipStatus } from "./dispatches";

export type { MachineStatus, WipStatus };

// ---------- Current snapshot types (Phase A backend) ----------

export type ThresholdColor = "neutral" | "orange" | "red";
export type TriageType = "pending_approval" | "escalated_issue" | "open_issue";
export type TrendArrow = "up" | "flat" | "down";

export interface KpiCardData {
  value: number;
  delta_24h: number;
  threshold_color: ThresholdColor;
}

export interface KpiBar {
  new_orders: KpiCardData;
  completed: KpiCardData;
  returned: KpiCardData;
  pending_approval: KpiCardData;
  open_critical_high_issues: KpiCardData;
}

export interface MachineGrid {
  machine_id: string;
  machine_no: string;
  lab_name: string;
  status: string; // canonical English MachineStatus value
  today_hours: number;
  current_recipe: string | null;
  current_operator: string | null;
  est_completion_at: string | null;
}

export interface MachineHeatmap {
  by_lab: Record<string, MachineGrid[]>;
  avg_utilization_pct: number;
  in_use_count: number;
  total_count: number;
}

// Pydantic `tuple[int, int]` serializes as a JSON array `[number, number]`.
export type Pair = [number, number]; // (now_count, delta_24h)

export interface WipPipeline {
  total: number;
  waiting_dispatch: Pair;
  dispatched: Pair;
  in_progress: Pair;
  awaiting_handoff: Pair;
  done: Pair;
  terminated: Pair;
}

export interface TriageItem {
  type: TriageType;
  ref_id: string;
  label: string;
  lab_name: string | null;
  severity: Severity | null;
  created_at: string;
}

export interface EscalationRow {
  issue_id: string;
  lab_name: string;
  severity: Severity;
  escalation_level: number;
  title: string;
  escalated_at: string;
}

export interface CompletionRow {
  wip_no: string;
  order_no: string;
  lab_name: string;
  returned_at: string;
}

export interface LabRow {
  lab_name: string;
  completed_today: number;
  awaiting_handoff: number;
  open_high_critical_issues: number;
  avg_utilization_pct: number;
  trend_24h: TrendArrow;
}

export interface DashboardSnapshot {
  viewer_role: "lab_supervisor" | "general_supervisor";
  viewer_lab: string | null;
  generated_at: string;

  kpi: KpiBar;
  machines: MachineHeatmap;
  wip_pipeline: WipPipeline;
  triage: TriageItem[];
  recent_escalations: EscalationRow[];
  // Mutually exclusive based on role:
  //   lab_supervisor → recent_completions, lab_leaderboard = null
  //   general_supervisor → lab_leaderboard, recent_completions = null
  recent_completions: CompletionRow[] | null;
  lab_leaderboard: LabRow[] | null;
}
