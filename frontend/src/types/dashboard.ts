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

// ---------- Deprecated (kept until Phase E scrubs consumers) ----------
//
// These types belong to the legacy C/D dispatch dashboard and the Sprint 4
// supervisor dashboard. Both surfaces are about to be removed:
//   - frontend/app/_dashboard/{Attention,Dispatch,Labs,MachineStatus}Panel.tsx
//   - the Sprint 4 layout in frontend/app/page.tsx
// Phase E of the redesign deletes those files; until then we keep these
// aliases so the codebase type-checks.

/** @deprecated removed in Phase E (C/D dispatch dashboard). */
export interface DashboardKpis {
  pendingDispatches: number;
  schedulingDispatches: number;
  readyDispatches: number;
  blockedMachines: number;
  machineCount: number;
  avgUtilization: number;
}

/** @deprecated removed in Phase E (C/D dispatch dashboard). */
export interface DashboardLab {
  lab: string;
  machineCount: number;
  dispatchCount: number;
  pendingCount: number;
  schedulingCount: number;
  readyCount: number;
  blockedMachineCount: number;
  avgUtilization: number;
}

/** @deprecated removed in Phase E (C/D dispatch dashboard). */
export interface DashboardMachine {
  machineId: string;
  name: string;
  lab: string;
  status: MachineStatus;
  utilization: number;
}

/** @deprecated removed in Phase E (C/D dispatch dashboard). */
export interface DashboardDispatch {
  dispatchId: string;
  wipId: string;
  orderId: string;
  lab: string;
  experimentItem: string;
  priority: string;
  dueAt: string;
  status: WipStatus;
  suggestedMachineId?: string | null;
  scheduledStart?: string | null;
  scheduledEnd?: string | null;
}

/** @deprecated removed in Phase E (C/D dispatch dashboard). */
export interface DashboardData {
  scope: string;
  user: { name: string; role: string; lab?: string | null };
  kpis: DashboardKpis;
  labs: DashboardLab[];
  machines: DashboardMachine[];
  dispatches: DashboardDispatch[];
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface IssuesSummary {
  totalOpen: number;
  bySeverity: Record<string, number>;
  createdToday: number;
  escalatedToday: number;
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface LabBreakdown {
  labId: string;
  labCode: string;
  labName: string;
  openIssues: number;
  escalatedIssues: number;
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface RecentEscalation {
  id: string;
  title: string;
  severity: Severity;
  escalationLevel: number;
  labId: string;
  updatedAt: string;
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface MachineLabBreakdown {
  labCode: string;
  byStatus: Record<string, number>;
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface MachinesSummary {
  total: number;
  byStatus: Record<string, number>;
  avgUtilization: number;
  byLab: MachineLabBreakdown[];
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface OrderLabBreakdown {
  labCode: string;
  byBucket: Record<string, number>;
}

/** @deprecated removed in Phase E (Sprint 4 supervisor dashboard). */
export interface OrdersSummary {
  total: number;
  byBucket: Record<string, number>;
  byLab: OrderLabBreakdown[];
}
