"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import UserSwitcher, {
  authHeaders,
  type AppUser,
} from "@/components/UserSwitcher";
import { formatLab } from "@/components/labDisplay";
import KpiCard from "@/components/ui/KpiCard";
import Chip from "@/components/ui/Chip";

type MachineStatus = "閒置" | "使用中" | "保養中" | "故障中" | "停用";
type WipStatus = "待派工" | "排程中" | "待上機";

type DashboardPayload = {
  scope: string;
  user: { name: string; role: string; lab?: string | null };
  kpis: {
    pendingDispatches: number;
    schedulingDispatches: number;
    readyDispatches: number;
    blockedMachines: number;
    machineCount: number;
    avgUtilization: number;
  };
  labs: {
    lab: string;
    machineCount: number;
    dispatchCount: number;
    pendingCount: number;
    schedulingCount: number;
    readyCount: number;
    blockedMachineCount: number;
    avgUtilization: number;
  }[];
  machines: {
    machineId: string;
    name: string;
    lab: string;
    status: MachineStatus;
    utilization: number;
  }[];
  dispatches: {
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
  }[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const statusTypes: Record<WipStatus, "pending" | "review" | "approved"> = {
  待派工: "pending",
  排程中: "review",
  待上機: "approved",
};

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [message, setMessage] = useState("讀取資料庫中");

  const loadDashboard = useCallback((user?: AppUser) => {
    fetch(`${apiUrl}/api/dashboard`, { headers: authHeaders(user?.userId) })
      .then((res) =>
        res.ok ? res.json() : Promise.reject(new Error("dashboard failed")),
      )
      .then((payload: { data: DashboardPayload }) => {
        setDashboard(payload.data);
        setMessage("已連線 PostgreSQL");
      })
      .catch(() => setMessage("後端或 PostgreSQL 尚未啟動"));
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const isGlobalView = dashboard?.scope === "all";
  const blockedMachines = useMemo(
    () =>
      dashboard?.machines.filter((machine) =>
        ["故障中", "保養中", "停用"].includes(machine.status),
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
            {dashboard?.user.role ?? "角色"} · {message}
          </p>
        </div>
        <UserSwitcher onChange={loadDashboard} />
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
          value={dashboard?.kpis.pendingDispatches ?? 0}
          sub={isGlobalView ? "跨 LAB 待排" : "本實驗室待排"}
          color="var(--blue)"
          icon="📋"
        />
        <KpiCard
          label="排程中"
          value={dashboard?.kpis.schedulingDispatches ?? 0}
          sub="已產生系統預估"
          color="var(--cyan)"
          icon="🗂️"
        />
        <KpiCard
          label="不可用機台"
          value={dashboard?.kpis.blockedMachines ?? 0}
          sub="故障、保養或停用"
          color="var(--red)"
          icon="⚠️"
        />
        <KpiCard
          label="平均稼動率"
          value={`${dashboard?.kpis.avgUtilization ?? 0}%`}
          sub={`${dashboard?.kpis.machineCount ?? 0} 台機台`}
          color="var(--green)"
          icon="📈"
        />
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16 }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={panelStyle}>
            <div style={panelHeaderStyle}>
              <span style={{ fontWeight: 700 }}>
                {isGlobalView ? "各 LAB 情況" : "本 LAB 情況"}
              </span>
              <span style={badgeStyle}>{dashboard?.labs.length ?? 0} LAB</span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3,1fr)",
                gap: 12,
                padding: 16,
              }}
            >
              {(dashboard?.labs ?? []).map((lab) => (
                <div key={lab.lab} style={labCardStyle}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 10,
                    }}
                  >
                    <strong>{formatLab(lab.lab)}</strong>
                    <span style={badgeStyle}>{lab.avgUtilization}%</span>
                  </div>
                  <Metric label="WIP" value={lab.dispatchCount} />
                  <Metric label="待派工" value={lab.pendingCount} />
                  <Metric label="排程中" value={lab.schedulingCount} />
                  <Metric
                    label="不可用機台"
                    value={lab.blockedMachineCount}
                    danger={lab.blockedMachineCount > 0}
                  />
                </div>
              ))}
            </div>
          </div>

          <div style={panelStyle}>
            <div style={panelHeaderStyle}>
              <span style={{ fontWeight: 700 }}>WIP 進度追蹤</span>
              <span style={badgeStyle}>
                {dashboard?.dispatches.length ?? 0} 筆
              </span>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--s2)" }}>
                  {[
                    "WIP",
                    "LAB",
                    "實驗項目",
                    "優先",
                    "狀態",
                    "機台",
                    "預估時間",
                  ].map((header) => (
                    <th key={header} style={thStyle}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(dashboard?.dispatches ?? []).slice(0, 8).map((dispatch) => (
                  <tr
                    key={dispatch.dispatchId}
                    style={{ borderBottom: "1px solid var(--border2)" }}
                  >
                    <td style={tdStyle}>
                      {dispatch.wipId}
                      <br />
                      <span style={{ color: "var(--text3)" }}>
                        {dispatch.orderId}
                      </span>
                    </td>
                    <td style={tdStyle}>{formatLab(dispatch.lab)}</td>
                    <td style={tdStyle}>{dispatch.experimentItem}</td>
                    <td style={tdStyle}>{dispatch.priority}</td>
                    <td style={tdStyle}>
                      <Chip
                        type={statusTypes[dispatch.status]}
                        label={dispatch.status}
                      />
                    </td>
                    <td style={tdStyle}>
                      {dispatch.suggestedMachineId ?? "-"}
                    </td>
                    <td style={tdStyle}>
                      {dispatch.scheduledStart ?? "-"}
                      <br />
                      <span style={{ color: "var(--text3)" }}>
                        {dispatch.scheduledEnd ?? ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={panelStyle}>
            <div style={panelHeaderStyle}>
              <span style={{ fontWeight: 700 }}>機台狀態</span>
              <span style={badgeStyle}>
                {dashboard?.machines.length ?? 0} 台
              </span>
            </div>
            {(dashboard?.machines ?? []).slice(0, 8).map((machine) => (
              <div
                key={machine.machineId}
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border2)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 8,
                  }}
                >
                  <span
                    style={{ fontFamily: "monospace", color: "var(--text)" }}
                  >
                    {machine.machineId}
                  </span>
                  <span
                    style={{
                      color:
                        machine.status === "閒置"
                          ? "var(--green)"
                          : machine.status === "使用中"
                            ? "var(--blue)"
                            : "var(--red)",
                      fontSize: 11,
                    }}
                  >
                    {machine.status}
                  </span>
                </div>
                <div
                  style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}
                >
                  {formatLab(machine.lab)} · {machine.name}
                </div>
                <div
                  style={{
                    height: 5,
                    background: "var(--s3)",
                    borderRadius: 3,
                    overflow: "hidden",
                    marginTop: 8,
                  }}
                >
                  <div
                    style={{
                      width: `${machine.utilization}%`,
                      height: "100%",
                      background:
                        "linear-gradient(90deg,var(--blue),var(--cyan))",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div style={panelStyle}>
            <div style={panelHeaderStyle}>
              <span style={{ fontWeight: 700 }}>需注意</span>
              <span style={badgeStyle}>{blockedMachines.length} 項</span>
            </div>
            {(blockedMachines.length ? blockedMachines : []).map((machine) => (
              <div
                key={machine.machineId}
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border2)",
                  fontSize: 12,
                }}
              >
                <strong style={{ color: "var(--orange)" }}>
                  {machine.machineId}
                </strong>
                <span style={{ color: "var(--text2)" }}>
                  {" "}
                  · {formatLab(machine.lab)} · {machine.status}
                </span>
              </div>
            ))}
            {!blockedMachines.length && (
              <div style={{ padding: 16, color: "var(--text3)", fontSize: 12 }}>
                目前沒有故障、保養或停用機台。
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: number;
  danger?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        color: "var(--text2)",
        fontSize: 12,
        marginTop: 6,
      }}
    >
      <span>{label}</span>
      <strong style={{ color: danger ? "var(--red)" : "var(--text)" }}>
        {value}
      </strong>
    </div>
  );
}

const panelStyle = {
  background: "var(--s1)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  overflow: "hidden",
};
const panelHeaderStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "14px 18px",
  borderBottom: "1px solid var(--border2)",
};
const badgeStyle = {
  fontSize: 10,
  fontFamily: "monospace",
  color: "var(--text3)",
  background: "var(--s3)",
  padding: "2px 7px",
  borderRadius: 4,
};
const labCardStyle = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 8,
  padding: 14,
};
const thStyle = {
  fontSize: 10,
  letterSpacing: 1.5,
  color: "var(--text3)",
  padding: "10px 16px",
  textAlign: "left" as const,
  fontFamily: "monospace",
  borderBottom: "1px solid var(--border2)",
};
const tdStyle = {
  padding: "12px 16px",
  fontSize: 12.5,
  color: "var(--text2)",
  verticalAlign: "middle" as const,
};
