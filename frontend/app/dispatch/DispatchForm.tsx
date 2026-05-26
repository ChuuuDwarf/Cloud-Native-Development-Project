"use client";

import { useEffect, useState } from "react";
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
  prefill,
  prefillNonce,
}: {
  experimentItems: string[];
  submitting: boolean;
  onSubmit: (payload: CreateDispatchPayload) => void;
  // 由「待排程 WIP」挑單帶入；手打仍可直接編輯這些欄位。
  prefill?: Partial<FormState> | null;
  prefillNonce?: number;
}) {
  const [form, setForm] = useState<FormState>(EMPTY);

  // 每次挑單（prefillNonce 變動）就把 WIP 資料填入表單；之後仍可手動編輯。
  useEffect(() => {
    if (prefill) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({ ...EMPTY, ...prefill });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefillNonce]);

  const set = (patch: Partial<FormState>) => setForm({ ...form, ...patch });

  function submit() {
    onSubmit({ ...form, dueAt: toApiDateTime(form.dueAt) });
  }

  return (
    <Panel
      title="新增待排程 WIP"
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
  // 沒有 border-box 時，100% 寬 + padding 會撐出欄寬，datetime-local 的日期選擇圖示
  // 被裁切到面板外而點不到。
  boxSizing: "border-box",
  minWidth: 0,
};
