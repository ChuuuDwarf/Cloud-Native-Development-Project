"use client";

import { useQuery } from "@tanstack/react-query";
import { PermissionGuard } from "@/components/PermissionGuard";
import { dashboardApi } from "@/services/dashboard-api";
import KpiBar from "@/app/_dashboard/KpiBar";
import MachineHeatmap from "@/app/_dashboard/MachineHeatmap";
import WipPipeline from "@/app/_dashboard/WipPipeline";
import TriageList from "@/app/_dashboard/TriageList";
import EscalationsList from "@/app/_dashboard/EscalationsList";
import ThroughputChart from "@/app/_dashboard/ThroughputChart";
import LabLeaderboard from "@/app/_dashboard/LabLeaderboard";
import { useDashboardStream } from "@/app/_dashboard/useDashboardStream";

export default function DashboardPage() {
  return (
    <PermissionGuard requiredPermission="dashboard:read">
      <DashboardContent />
    </PermissionGuard>
  );
}

function DashboardContent() {
  useDashboardStream();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.getSnapshot(),
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return <div style={{ padding: 24, color: "var(--text2)" }}>載入中…</div>;
  }
  if (isError) {
    return (
      <div style={{ padding: 24, color: "var(--red)" }}>
        儀表板載入失敗：{(error as Error).message}
      </div>
    );
  }
  if (!data) return null;

  const isCrossLab = data.viewer_role === "general_supervisor";

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, margin: 0 }}>
          主管儀表板
        </h1>
        <p
          style={{
            fontSize: 12,
            color: "var(--text3)",
            marginTop: 4,
            fontFamily: "monospace",
          }}
        >
          SUPERVISOR DASHBOARD · {isCrossLab ? "全廠視角" : `${data.viewer_lab ?? "本 lab"}`} ·
          自動更新
        </p>
      </div>

      {/* Top: KPI Bar */}
      <div style={{ marginBottom: 16 }}>
        <KpiBar data={data.kpi} />
      </div>

      {/* Mid: Heatmap | Pipeline */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <MachineHeatmap data={data.machines} showLabPrefix={isCrossLab} />
        <WipPipeline data={data.wip_pipeline} />
      </div>

      {/* Bottom: 3 cols */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 16,
        }}
      >
        <TriageList items={data.triage} />
        <EscalationsList rows={data.recent_escalations} />
        {isCrossLab ? (
          <LabLeaderboard rows={data.lab_leaderboard ?? []} />
        ) : (
          <ThroughputChart data={data.throughput_24h ?? []} />
        )}
      </div>
    </div>
  );
}
