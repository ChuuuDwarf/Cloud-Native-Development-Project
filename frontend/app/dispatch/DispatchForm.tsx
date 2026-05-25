"use client";

import { useState } from "react";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import type { CreateDispatchPayload } from "@/types/dispatches";

const PRIORITIES = ["一般", "高", "特急"];

const EMPTY: FormState = {
  dispatchId: "",
  wipId: "",
  orderId: "",
  experimentItem: "",
  priority: "一般",
  dueAt: "",
};

const DEMO: FormState = {
  dispatchId: "DSP-004",
  wipId: "WIP-004",
  orderId: "WO-004",
  experimentItem: "表面形貌分析",
  priority: "高",
  dueAt: "2026-05-24T12:00",
};

type FormState = {
  dispatchId: string;
  wipId: string;
  orderId: string;
  experimentItem: string;
  priority: string;
  dueAt: string;
};

function toApiDateTime(value: string) {
  return value.replace("T", " ");
}

export default function DispatchForm({
  experimentItems,
  submitting,
  onSubmit,
}: {
  experimentItems: string[];
  submitting: boolean;
  onSubmit: (payload: CreateDispatchPayload) => void;
}) {
  const [form, setForm] = useState<FormState>(EMPTY);

  const set = (patch: Partial<FormState>) => setForm({ ...form, ...patch });

  function submit() {
    onSubmit({ ...form, dueAt: toApiDateTime(form.dueAt) });
  }

  return (
    <Panel
      title="新增待派工 WIP"
      action={
        <Btn small onClick={() => setForm(DEMO)}>
          快速填入
        </Btn>
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
          placeholder="Dispatch ID，例如 DSP-001"
          value={form.dispatchId}
          onChange={(e) => set({ dispatchId: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="WIP ID，例如 WIP-001"
          value={form.wipId}
          onChange={(e) => set({ wipId: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="委託單 ID，例如 WO-001"
          value={form.orderId}
          onChange={(e) => set({ orderId: e.target.value })}
          style={inputStyle}
        />
        <select
          value={form.experimentItem}
          onChange={(e) => set({ experimentItem: e.target.value })}
          style={inputStyle}
        >
          <option value="">選擇實驗項目</option>
          {experimentItems.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          value={form.priority}
          onChange={(e) => set({ priority: e.target.value })}
          style={inputStyle}
        >
          {PRIORITIES.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <input
          type="datetime-local"
          value={form.dueAt}
          onChange={(e) => set({ dueAt: e.target.value })}
          style={inputStyle}
        />
        <Btn variant="primary" disabled={submitting} onClick={submit}>
          {submitting ? "新增中…" : "新增 WIP"}
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
