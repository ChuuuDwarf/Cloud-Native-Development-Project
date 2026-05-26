import { httpClient } from "@/api/httpClient";
import type { ApiResponse } from "@/types/api";
import type { DashboardData, DashboardSnapshot } from "@/types/dashboard";

export type {
  DashboardData,
  DashboardDispatch,
  DashboardKpis,
  DashboardLab,
  DashboardMachine,
  DashboardSnapshot,
  MachineStatus,
  WipStatus,
} from "@/types/dashboard";

export const dashboardApi = {
  // E supervisor view (Sprint 4) — used by the home `/` dashboard.
  async getSnapshot(): Promise<DashboardSnapshot> {
    const res = await httpClient.get<ApiResponse<DashboardSnapshot>>("/dashboard");
    return res.data.data;
  },
  // C/D dispatch view — kept for backward compat with main; backend route
  // for this shape isn't implemented in this branch, so calling this will
  // 404 / return the supervisor shape. Will be revisited if/when the
  // dispatch dashboard finds a home (e.g. /dispatch).
  async fetch(): Promise<DashboardData> {
    const res = await httpClient.get<ApiResponse<DashboardData>>("/dashboard/dispatch");
    return res.data.data;
  },
};
