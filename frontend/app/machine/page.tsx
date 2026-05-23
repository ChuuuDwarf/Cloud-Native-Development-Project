"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import UserSwitcher, {
  authHeaders,
  type AppUser,
} from "@/components/UserSwitcher";
import { formatLab } from "@/components/labDisplay";
import Chip from "@/components/ui/Chip";
import KpiCard from "@/components/ui/KpiCard";

type MachineStatus = "閒置" | "使用中" | "保養中" | "故障中" | "停用";

type Machine = {
  machineId: string;
  name: string;
  lab: string;
  status: MachineStatus;
  supportedItems: string[];
  utilization: number;
  owner: string;
  lastMaintenance: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const statuses: MachineStatus[] = [
  "閒置",
  "使用中",
  "保養中",
  "故障中",
  "停用",
];
const statusTypes: Record<
  MachineStatus,
  "idle" | "running" | "pending" | "rejected"
> = {
  閒置: "idle",
  使用中: "running",
  保養中: "pending",
  故障中: "rejected",
  停用: "rejected",
};

const demoMachineForm = {
  machineId: "AFM-004",
  name: "原子力顯微鏡",
  lab: "LAB A",
  supportedItems: "表面形貌分析, 粗糙度量測",
  owner: "林育誠",
  utilization: "18",
  lastMaintenance: "2026-05-20",
};

export default function MachinePage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<MachineStatus>("閒置");
  const [message, setMessage] = useState("讀取資料庫中");
  const [form, setForm] = useState({
    machineId: "",
    name: "",
    lab: "",
    supportedItems: "",
    owner: "",
    utilization: "0",
    lastMaintenance: "尚未保養",
  });

  const loadMachines = useCallback((user?: AppUser) => {
    fetch(`${apiUrl}/api/machines`, { headers: authHeaders(user?.userId) })
      .then((res) =>
        res.ok ? res.json() : Promise.reject(new Error("load failed")),
      )
      .then((payload: { data: Machine[] }) => {
        setMachines(payload.data);
        setMessage("已連線 PostgreSQL");
      })
      .catch(() => setMessage("後端或 PostgreSQL 尚未啟動"));
  }, []);

  useEffect(() => {
    loadMachines();
  }, [loadMachines]);

  const summary = useMemo(() => {
    const available = machines.filter(
      (machine) => machine.status === "閒置",
    ).length;
    const blocked = machines.filter((machine) =>
      ["故障中", "保養中", "停用"].includes(machine.status),
    ).length;
    const avg = machines.length
      ? Math.round(
          machines.reduce((sum, machine) => sum + machine.utilization, 0) /
            machines.length,
        )
      : 0;
    return { available, blocked, avg };
  }, [machines]);

  function createMachine() {
    const existingMachine = machines.find(
      (machine) => machine.machineId === form.machineId,
    );
    fetch(
      `${apiUrl}/api/machines${existingMachine ? `/${form.machineId}` : ""}`,
      {
        method: existingMachine ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          machineId: form.machineId,
          name: form.name,
          lab: form.lab,
          supportedItems: form.supportedItems
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          owner: form.owner,
          utilization: Number(form.utilization),
          lastMaintenance: form.lastMaintenance,
        }),
      },
    )
      .then((res) =>
        res.ok ? res.json() : Promise.reject(new Error("create failed")),
      )
      .then(() => {
        setForm({
          machineId: "",
          name: "",
          lab: "",
          supportedItems: "",
          owner: "",
          utilization: "0",
          lastMaintenance: "尚未保養",
        });
        loadMachines();
      })
      .catch(() =>
        setMessage("儲存機台失敗，請確認使用者權限、ID 不重複且後端已啟動"),
      );
  }

  function updateStatus(machineId: string) {
    fetch(`${apiUrl}/api/machines/${machineId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status: selectedStatus }),
    })
      .then((res) =>
        res.ok ? res.json() : Promise.reject(new Error("update failed")),
      )
      .then(() => loadMachines())
      .catch(() => setMessage("更新機台狀態失敗，廠區使用者與主管不可操作"));
  }

  function editMachine(machine: Machine) {
    setForm({
      machineId: machine.machineId,
      name: machine.name,
      lab: machine.lab,
      supportedItems: machine.supportedItems.join(", "),
      owner: machine.owner,
      utilization: String(machine.utilization),
      lastMaintenance: machine.lastMaintenance,
    });
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 22,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>機台管理</h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--text3)",
              marginTop: 4,
              fontFamily: "monospace",
            }}
          >
            ROLE C · POSTGRESQL · {message}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <UserSwitcher onChange={loadMachines} />
          <select
            value={selectedStatus}
            onChange={(event) =>
              setSelectedStatus(event.target.value as MachineStatus)
            }
            style={inputStyle}
          >
            {statuses.map((status) => (
              <option key={status}>{status}</option>
            ))}
          </select>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 14,
          marginBottom: 20,
        }}
      >
        <KpiCard
          label="機台總數"
          value={machines.length}
          sub="來自 PostgreSQL"
          color="var(--blue)"
          icon="⚙️"
        />
        <KpiCard
          label="可派工機台"
          value={summary.available}
          sub="狀態為閒置"
          color="var(--green)"
          icon="✅"
        />
        <KpiCard
          label="不可派工"
          value={summary.blocked}
          sub="保養、故障或停用"
          color="var(--red)"
          icon="⚠️"
        />
        <KpiCard
          label="平均稼動率"
          value={`${summary.avg}%`}
          sub="由機台資料計算"
          color="var(--cyan)"
          icon="📈"
        />
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}
      >
        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>新增機台</span>
            <button
              onClick={() => setForm(demoMachineForm)}
              style={smallButtonStyle}
            >
              快速填入
            </button>
          </div>
          <div
            style={{
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <input
              placeholder="機台 ID，例如 XRD-002"
              value={form.machineId}
              onChange={(event) =>
                setForm({ ...form, machineId: event.target.value })
              }
              style={inputStyle}
            />
            <input
              placeholder="機台名稱"
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              style={inputStyle}
            />
            <select
              value={form.lab}
              onChange={(event) =>
                setForm({ ...form, lab: event.target.value })
              }
              style={inputStyle}
            >
              <option value="">選擇實驗室</option>
              {["LAB A", "LAB B", "LAB C"].map((lab) => (
                <option key={lab} value={lab}>
                  {formatLab(lab)}
                </option>
              ))}
            </select>
            <input
              placeholder="支援項目，用逗號分隔"
              value={form.supportedItems}
              onChange={(event) =>
                setForm({ ...form, supportedItems: event.target.value })
              }
              style={inputStyle}
            />
            <input
              placeholder="負責人"
              value={form.owner}
              onChange={(event) =>
                setForm({ ...form, owner: event.target.value })
              }
              style={inputStyle}
            />
            <input
              placeholder="稼動率 0-100"
              value={form.utilization}
              onChange={(event) =>
                setForm({ ...form, utilization: event.target.value })
              }
              style={inputStyle}
            />
            <input
              placeholder="上次保養日"
              value={form.lastMaintenance}
              onChange={(event) =>
                setForm({ ...form, lastMaintenance: event.target.value })
              }
              style={inputStyle}
            />
            <button onClick={createMachine} style={buttonStyle}>
              {machines.some((machine) => machine.machineId === form.machineId)
                ? "儲存編輯"
                : "新增機台"}
            </button>
          </div>
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>機台清單</span>
            <span style={badgeStyle}>{machines.length} 筆</span>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--s2)" }}>
                {[
                  "機台",
                  "實驗室",
                  "狀態",
                  "支援項目",
                  "稼動率",
                  "保養日",
                  "操作",
                ].map((header) => (
                  <th key={header} style={thStyle}>
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {machines.map((machine) => (
                <tr
                  key={machine.machineId}
                  style={{ borderBottom: "1px solid var(--border2)" }}
                >
                  <td style={tdStyle}>
                    <div
                      style={{ fontFamily: "monospace", color: "var(--text)" }}
                    >
                      {machine.machineId}
                    </div>
                    <div style={{ color: "var(--text3)", fontSize: 11 }}>
                      {machine.name} · {machine.owner}
                    </div>
                  </td>
                  <td style={tdStyle}>{formatLab(machine.lab)}</td>
                  <td style={tdStyle}>
                    <Chip
                      type={statusTypes[machine.status]}
                      label={machine.status}
                    />
                  </td>
                  <td style={tdStyle}>{machine.supportedItems.join("、")}</td>
                  <td style={tdStyle}>{machine.utilization}%</td>
                  <td style={tdStyle}>{machine.lastMaintenance}</td>
                  <td style={tdStyle}>
                    <button
                      onClick={() => editMachine(machine)}
                      style={smallButtonStyle}
                    >
                      編輯
                    </button>{" "}
                    <button
                      onClick={() => updateStatus(machine.machineId)}
                      style={buttonStyle}
                    >
                      套用狀態
                    </button>
                  </td>
                </tr>
              ))}
              {!machines.length && (
                <tr>
                  <td
                    colSpan={7}
                    style={{ ...tdStyle, textAlign: "center", padding: 28 }}
                  >
                    尚無機台，請先從左側新增。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
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
const inputStyle = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "9px 10px",
  borderRadius: 8,
  fontSize: 12,
  width: "100%",
};
const buttonStyle = {
  background: "var(--blue)",
  border: "1px solid var(--border)",
  color: "#fff",
  padding: "7px 10px",
  borderRadius: 6,
  fontSize: 11,
  cursor: "pointer",
};
const smallButtonStyle = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text2)",
  padding: "4px 8px",
  borderRadius: 6,
  fontSize: 10,
  cursor: "pointer",
};
