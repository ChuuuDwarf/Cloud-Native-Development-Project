"use client";

import { useState } from "react";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { Machine, MachinePayload } from "@/types/machines";

const LABS = ["LAB-A", "LAB-B", "LAB-C"];

const DEMO: FormState = {
  machineId: "AFM-004",
  name: "原子力顯微鏡",
  lab: "LAB-A",
  supportedItems: "表面形貌分析, 粗糙度量測",
  owner: "林育誠",
  utilization: "18",
  lastMaintenance: "2026-05-20",
};

const EMPTY: FormState = {
  machineId: "",
  name: "",
  lab: "",
  supportedItems: "",
  owner: "",
  utilization: "0",
  lastMaintenance: "尚未保養",
};

/** Form fields are all strings while editing; converted to a payload on submit. */
type FormState = {
  machineId: string;
  name: string;
  lab: string;
  supportedItems: string;
  owner: string;
  utilization: string;
  lastMaintenance: string;
};

function toFormState(machine: Machine): FormState {
  return {
    machineId: machine.machineId,
    name: machine.name,
    lab: machine.lab,
    supportedItems: machine.supportedItems.join(", "),
    owner: machine.owner,
    utilization: String(machine.utilization),
    lastMaintenance: machine.lastMaintenance,
  };
}

export default function MachineForm({
  initial,
  submitting,
  onSubmit,
}: {
  /** Machine being edited, or null for a fresh create form. */
  initial: Machine | null;
  submitting: boolean;
  onSubmit: (payload: MachinePayload) => void;
}) {
  const [form, setForm] = useState<FormState>(initial ? toFormState(initial) : EMPTY);

  const isEdit = initial !== null;
  const set = (patch: Partial<FormState>) => setForm({ ...form, ...patch });

  function submit() {
    onSubmit({
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
    });
  }

  return (
    <Panel
      title={isEdit ? "編輯機台" : "新增機台"}
      action={
        !isEdit && (
          <Btn small onClick={() => setForm(DEMO)}>
            快速填入
          </Btn>
        )
      }
    >
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
          disabled={isEdit}
          onChange={(e) => set({ machineId: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="機台名稱"
          value={form.name}
          onChange={(e) => set({ name: e.target.value })}
          style={inputStyle}
        />
        <select value={form.lab} onChange={(e) => set({ lab: e.target.value })} style={inputStyle}>
          <option value="">選擇實驗室</option>
          {LABS.map((lab) => (
            <option key={lab} value={lab}>
              {formatLab(lab)}
            </option>
          ))}
        </select>
        <input
          placeholder="支援項目，用逗號分隔"
          value={form.supportedItems}
          onChange={(e) => set({ supportedItems: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="負責人"
          value={form.owner}
          onChange={(e) => set({ owner: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="稼動率 0-100"
          value={form.utilization}
          onChange={(e) => set({ utilization: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="上次保養日"
          value={form.lastMaintenance}
          onChange={(e) => set({ lastMaintenance: e.target.value })}
          style={inputStyle}
        />
        <Btn variant="primary" disabled={submitting} onClick={submit}>
          {submitting ? "儲存中…" : isEdit ? "儲存編輯" : "新增機台"}
        </Btn>
      </div>
    </Panel>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "9px 10px",
  borderRadius: 8,
  fontSize: 12,
  width: "100%",
};
