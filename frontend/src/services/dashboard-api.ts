import { httpClient } from "@/api/httpClient";
import type { ApiResponse } from "@/types/api";
import type { DashboardSnapshot } from "@/types/dashboard";

export type {
  DashboardSnapshot,
  EscalationRow,
  KpiBar,
  KpiCardData,
  LabRow,
  MachineGrid,
  MachineHeatmap,
  ThroughputPoint,
  TriageItem,
  WipPipeline,
} from "@/types/dashboard";

export const dashboardApi = {
  /**
   * Fetch the supervisor dashboard snapshot.
   *
   * Backend returns a complete `DashboardSnapshot` keyed by viewer role —
   * `throughput_24h` and `lab_leaderboard` are mutually-null based on
   * whether the caller is `lab_supervisor` or `general_supervisor`.
   */
  async getSnapshot(): Promise<DashboardSnapshot> {
    const res = await httpClient.get<ApiResponse<DashboardSnapshot>>("/dashboard");
    return res.data.data;
  },
};
