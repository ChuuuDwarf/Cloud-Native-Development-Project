"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import KpiCard from "@/components/ui/KpiCard";
import { formatLab } from "@/components/labDisplay";
import { dashboardApi } from "@/services/dashboard-api";
import LabsPanel from "./_dashboard/LabsPanel";
import DispatchPanel from "./_dashboard/DispatchPanel";
import MachineStatusPanel from "./_dashboard/MachineStatusPanel";
import AttentionPanel from "./_dashboard/AttentionPanel";

const BLOCKED_STATUSES = ["故障中", "保養中", "停用"];

export default function Dashboard() {
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.fetch,
  });
  const dashboard = dashboardQuery.data;

  const isGlobalView = dashboard?.scope === "all";
  const blockedMachines = useMemo(
    () =>
      dashboard?.machines?.filter((machine) =>
        BLOCKED_STATUSES.includes(machine.status),
      ) ?? [],
    [dashboard],
  );

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 24,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>主管儀表板</h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--text3)",
              marginTop: 4,
              fontFamily: "monospace",
            }}
          >
            {isGlobalView ? "ALL LABS" : formatLab(dashboard?.scope)} ·{" "}
            {dashboard?.user?.role ?? "角色"} · {statusLine(dashboardQuery)}
          </p>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 14,
          marginBottom: 22,
        }}
      >
        <KpiCard
          label="待派工 WIP"
          value={dashboard?.kpis?.pendingDispatches ?? 0}
          sub={isGlobalView ? "跨 LAB 待排" : "本實驗室待排"}
          color="var(--blue)"
          icon="📋"
        />
        <KpiCard
          label="排程中"
          value={dashboard?.kpis?.schedulingDispatches ?? 0}
          sub="已產生系統預估"
          color="var(--cyan)"
          icon="🗂️"
        />
        <KpiCard
          label="不可用機台"
          value={dashboard?.kpis?.blockedMachines ?? 0}
          sub="故障、保養或停用"
          color="var(--red)"
          icon="⚠️"
        />
        <KpiCard
          label="平均稼動率"
          value={`${dashboard?.kpis?.avgUtilization ?? 0}%`}
          sub={`${dashboard?.kpis?.machineCount ?? 0} 台機台`}
          color="var(--green)"
          icon="📈"
        />
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16 }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <LabsPanel labs={dashboard?.labs ?? []} isGlobalView={isGlobalView} />
          <DispatchPanel dispatches={dashboard?.dispatches ?? []} />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <MachineStatusPanel machines={dashboard?.machines ?? []} />
          <AttentionPanel machines={blockedMachines} />
        </div>
      </div>
    </div>
  );
}

function statusLine(query: { isLoading: boolean; isError: boolean }): string {
  if (query.isLoading) return "讀取資料庫中";
  if (query.isError) return "後端或 PostgreSQL 尚未啟動";
  return "已連線 PostgreSQL";
}
