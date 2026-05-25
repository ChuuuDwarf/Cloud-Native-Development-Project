import { httpClient } from "@/api/httpClient";
import type { ApiResponse } from "@/types/api";
export type { DashboardData, DashboardDispatch, DashboardKpis, DashboardLab, DashboardMachine, MachineStatus, WipStatus } from "@/types/dashboard";
import type { DashboardData } from "@/types/dashboard";

export const dashboardApi = {
  async fetch(): Promise<DashboardData> {
    const res = await httpClient.get<ApiResponse<DashboardData>>("/dashboard");
    return res.data.data;
  },
};
