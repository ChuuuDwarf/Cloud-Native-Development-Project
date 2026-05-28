"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { issueApi } from "@/services/issue-api";
import { masterDataApi } from "@/services/master-data-api";
import { type Severity } from "@/constants/enums";
import { SeverityLabel } from "@/constants/status-labels";
import { machinesApi, type Machine } from "@/services/machines-api";

// Frontend-only demo helper: simulate a machine fault.
//
// Flow on submit:
//   1. POST /api/issues — fires the full notification chain (in-app + phone
//      to the engineer; Beat then escalates to supervisor → director).
//   2. PATCH /api/machines/{id}/status to 故障中 so the dashboard / machine
//      table reflect the simulated state.
//
// Step 1 first because that's what produces the visible alert behaviour the
// demo is showcasing. Step 2 failing is a cosmetic loss; step 1 failing
// aborts before touching machine state.

const SEVERITIES: Severity[] = ["low", "medium", "high", "critical"];

type Props = {
  machines: Machine[];
  onClose: () => void;
};

export default function SimulateIssueModal({ machines, onClose }: Props) {
  const queryClient = useQueryClient();
  const [machineId, setMachineId] = useState<string>(machines[0]?.machineId ?? "");
  const [severity, setSeverity] = useState<Severity>("high");
  const [title, setTitle] = useState("[模擬] 機台異常");
  const [description, setDescription] = useState("由 demo 按鈕觸發，測試 escalation 流程。");

  const masterDataQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: () => masterDataApi.fetch(),
  });
  const labs = masterDataQuery.data?.labs ?? [];

  const selectedMachine = useMemo(
    () => machines.find((m) => m.machineId === machineId),
    [machines, machineId]
  );

  const simulate = useMutation({
    mutationFn: async () => {
      if (!selectedMachine) throw new Error("沒有選擇機台");
      const lab = labs.find((l) => l.code === selectedMachine.lab);
      if (!lab) throw new Error(`找不到 lab code = ${selectedMachine.lab}`);

      // 1. Create the issue — this is the load-bearing call for the demo.
      const issue = await issueApi.create({
        type: "abnormal",
        targetType: "machine",
        targetId: selectedMachine.machineId,
        labId: lab.id,
        title,
        description,
        severity,
      });

      // 2. Flip status to 故障中 so the UI reflects the simulated state.
      // Best-effort — failure here doesn't unwind the issue.
      try {
        await machinesApi.updateStatus(selectedMachine.machineId, "故障中");
      } catch (err) {
        console.warn("status update failed; issue was still created", err);
      }
      return issue;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["machines"] });
      onClose();
      alert(
        "已建立異常 issue。\n" +
          "・lab_engineer 應在數秒內接到電話\n" +
          "・若未處理，~1 分鐘內升級到 lab_supervisor、再 ~1 分鐘到 大主管"
      );
    },
  });

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--s1)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: 20,
          width: 460,
          maxWidth: "90vw",
        }}
      >
        <h2 style={{ margin: 0, fontSize: 16, marginBottom: 4 }}>模擬機台異常</h2>
        <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 0, marginBottom: 16 }}>
          DEMO 用 — 會 create 一筆 abnormal issue 並把機台標為「故障中」，觸發完整 escalation 鏈。
        </p>

        <Field label="機台">
          <select value={machineId} onChange={(e) => setMachineId(e.target.value)} style={selectStyle}>
            {machines.length === 0 && <option value="">沒有機台可選</option>}
            {machines.map((m) => (
              <option key={m.machineId} value={m.machineId}>
                {m.machineId} — {m.name} ({m.lab}, {m.status})
              </option>
            ))}
          </select>
        </Field>

        <Field label="嚴重度">
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as Severity)}
            style={selectStyle}
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {SeverityLabel[s]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="標題">
          <input value={title} onChange={(e) => setTitle(e.target.value)} style={inputStyle} />
        </Field>

        <Field label="描述">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </Field>

        {simulate.error && (
          <div style={{ color: "var(--red)", fontSize: 12, marginTop: 8 }}>
            失敗：{(simulate.error as Error).message}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <button onClick={onClose} disabled={simulate.isPending} style={secondaryBtn}>
            取消
          </button>
          <button
            onClick={() => simulate.mutate()}
            disabled={simulate.isPending || !selectedMachine || labs.length === 0}
            style={primaryBtn}
          >
            {simulate.isPending ? "觸發中…" : "🚨 觸發異常"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div
        style={{
          fontSize: 11,
          color: "var(--text3)",
          marginBottom: 4,
          fontFamily: "monospace",
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "8px 10px",
  borderRadius: 6,
  fontSize: 13,
  boxSizing: "border-box",
};

const selectStyle: React.CSSProperties = { ...inputStyle, cursor: "pointer" };

const primaryBtn: React.CSSProperties = {
  background: "var(--red)",
  color: "#fff",
  border: "none",
  padding: "8px 16px",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
};

const secondaryBtn: React.CSSProperties = {
  background: "transparent",
  color: "var(--text2)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 13,
};
