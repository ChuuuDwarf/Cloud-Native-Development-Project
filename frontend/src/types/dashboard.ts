// Two dashboards coexist:
// - C/D dispatch dashboard (DashboardData) — machines + dispatches + utilization
// - E supervisor dashboard (DashboardSnapshot) — issues summary + escalations
// They share the same /api/dashboard backend route family but render at
// different paths in the frontend.

import type { Severity } from "@/constants/enums";
import type { MachineStatus } from "./machines";
import type { WipStatus } from "./dispatches";

export type { MachineStatus, WipStatus };

// ---------- C/D dispatch dashboard ----------

export interface DashboardKpis {
  pendingDispatches: number;
  schedulingDispatches: number;
  readyDispatches: number;
  blockedMachines: number;
  machineCount: number;
  avgUtilization: number;
}

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

export interface DashboardMachine {
  machineId: string;
  name: string;
  lab: string;
  status: MachineStatus;
  utilization: number;
}

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

export interface DashboardData {
  scope: string;
  user: { name: string; role: string; lab?: string | null };
  kpis: DashboardKpis;
  labs: DashboardLab[];
  machines: DashboardMachine[];
  dispatches: DashboardDispatch[];
}

// ---------- E supervisor dashboard (Sprint 4) ----------

export interface IssuesSummary {
  totalOpen: number;
  bySeverity: Record<string, number>;
  createdToday: number;
  escalatedToday: number;
}

export interface LabBreakdown {
  labId: string;
  labCode: string;
  labName: string;
  openIssues: number;
  escalatedIssues: number;
}

export interface RecentEscalation {
  id: string;
  title: string;
  severity: Severity;
  escalationLevel: number;
  labId: string;
  updatedAt: string;
}

// Sprint 6: machine + order widgets on the supervisor dashboard.

export interface MachineLabBreakdown {
  labCode: string;
  byStatus: Record<string, number>; // canonical English MachineStatus values
}

export interface MachinesSummary {
  total: number;
  byStatus: Record<string, number>;
  avgUtilization: number;
  byLab: MachineLabBreakdown[];
}

export interface OrderLabBreakdown {
  labCode: string;
  byBucket: Record<string, number>;
}

export interface OrdersSummary {
  total: number;
  byBucket: Record<string, number>;
  byLab: OrderLabBreakdown[];
}

export interface DashboardSnapshot {
  issues: IssuesSummary;
  unreadNotifications: number;
  byLab: LabBreakdown[];
  recentEscalations: RecentEscalation[];
  machines: MachinesSummary;
  orders: OrdersSummary;
}
