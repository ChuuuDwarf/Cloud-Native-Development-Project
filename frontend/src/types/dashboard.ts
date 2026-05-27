import type { MachineStatus } from "./machines";
import type { WipStatus } from "./dispatches";

export type { MachineStatus, WipStatus };

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
