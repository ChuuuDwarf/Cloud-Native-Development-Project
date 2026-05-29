"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import KpiCard from "@/components/ui/KpiCard";
import {
  machinesApi,
  type Machine,
  type MachinePayload,
  type MachineStatus,
} from "@/services/machines-api";
import MachineForm from "./MachineForm";
import MachineTable from "./MachineTable";
import SimulateIssueModal from "./SimulateIssueModal";

const STATUSES: MachineStatus[] = ["閒置", "使用中", "保養中", "故障中", "停用"];
const BLOCKED: MachineStatus[] = ["保養中", "故障中", "停用"];

export default function MachinePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const userLabCode = user?.role === "lab_supervisor" ? user.labCode : null;
  const [selectedStatus, setSelectedStatus] = useState<MachineStatus>("閒置");
  const [editing, setEditing] = useState<Machine | null>(null);
  // Bump to remount MachineForm so it clears after a successful create.
  const [formNonce, setFormNonce] = useState(0);
  const [simulateOpen, setSimulateOpen] = useState(false);

  const machinesQuery = useQuery({
    queryKey: ["machines"],
    queryFn: machinesApi.list,
  });
  const machines = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["machines"] });

  const save = useMutation({
    mutationFn: (payload: MachinePayload) =>
      machines.some((m) => m.machineId === payload.machineId)
        ? machinesApi.update(payload.machineId, payload)
        : machinesApi.create(payload),
    onSuccess: () => {
      invalidate();
      setEditing(null);
      setFormNonce((n) => n + 1);
    },
  });

  const applyStatus = useMutation({
    mutationFn: (machineId: string) => machinesApi.updateStatus(machineId, selectedStatus),
    onSuccess: invalidate,
  });

  const summary = useMemo(() => {
    const available = machines.filter((m) => m.status === "閒置").length;
    const blocked = machines.filter((m) => BLOCKED.includes(m.status)).length;
    const avg = machines.length
      ? Math.round(machines.reduce((sum, m) => sum + m.utilization, 0) / machines.length)
      : 0;
    return { available, blocked, avg };
  }, [machines]);

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
            {statusLine(machinesQuery, save.error ?? applyStatus.error)}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={() => setSimulateOpen(true)}
            disabled={machines.length === 0}
            title="DEMO 用：把選的機台標為故障並觸發 escalation 通知鏈"
            style={demoBtnStyle}
          >
            🚨 模擬機台異常
          </button>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value as MachineStatus)}
            style={selectStyle}
          >
            {STATUSES.map((status) => (
              <option key={status}>{status}</option>
            ))}
          </select>
        </div>
      </div>

      {simulateOpen && (
        <SimulateIssueModal machines={machines} onClose={() => setSimulateOpen(false)} />
      )}

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

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <MachineForm
          key={`${editing?.machineId ?? "new"}-${formNonce}`}
          initial={editing}
          submitting={save.isPending}
          onSubmit={(payload) => save.mutate(payload)}
          userLabCode={userLabCode}
        />
        <MachineTable
          machines={machines}
          applyLabel={selectedStatus}
          applying={applyStatus.isPending}
          onEdit={setEditing}
          onApplyStatus={(id) => applyStatus.mutate(id)}
        />
      </div>
    </div>
  );
}

function statusLine(
  query: { isLoading: boolean; isError: boolean },
  mutationError: unknown
): string {
  if (query.isLoading) return "讀取資料庫中…";
  if (query.isError) return "後端或 PostgreSQL 尚未啟動";
  if (mutationError) {
    const msg = extractApiError(mutationError);
    return msg ? `操作失敗：${msg}` : "操作失敗，請確認權限、ID 不重複且後端已啟動";
  }
  return "已連線 PostgreSQL";
}

function extractApiError(err: unknown): string | null {
  if (typeof err === "object" && err !== null) {
    const anyErr = err as {
      response?: { data?: { error?: { message?: string } } };
      message?: string;
    };
    return anyErr.response?.data?.error?.message ?? anyErr.message ?? null;
  }
  return null;
}

const selectStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "9px 10px",
  borderRadius: 8,
  fontSize: 12,
};

const demoBtnStyle: React.CSSProperties = {
  background: "var(--red)",
  color: "#fff",
  border: "none",
  padding: "9px 14px",
  borderRadius: 8,
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
};
