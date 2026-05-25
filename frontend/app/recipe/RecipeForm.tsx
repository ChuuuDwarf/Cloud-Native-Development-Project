"use client";

import { useMemo, useState } from "react";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { Machine } from "@/types/machines";
import type { RecipePayload } from "@/types/recipes";

const DEMO: FormState = {
  recipeId: "RCP-AFM-001",
  name: "AFM 表面形貌標準流程",
  version: "v1.0",
  experimentItem: "表面形貌分析",
  machineId: "AFM-004",
  method: "標準掃描模式，先做探針校正，再進行 5 點表面形貌量測。",
  parameters: "scanSize:10um,resolution:512,duration:30min",
  updatedBy: "",
};

const EMPTY: FormState = {
  recipeId: "",
  name: "",
  version: "",
  experimentItem: "",
  machineId: "",
  method: "",
  parameters: "",
  updatedBy: "",
};

/** Form fields are all strings while editing; converted to a payload on submit. */
type FormState = {
  recipeId: string;
  name: string;
  version: string;
  experimentItem: string;
  machineId: string;
  method: string;
  parameters: string;
  updatedBy: string;
};

function parseParameters(raw: string): Record<string, string> {
  return Object.fromEntries(
    raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => {
        const [key, value] = item.split(":");
        return [(key ?? "").trim(), (value ?? "").trim()];
      }),
  );
}

export default function RecipeForm({
  machines,
  experimentItems,
  submitting,
  onSubmit,
}: {
  machines: Machine[];
  /** Distinct experiment items, derived from machine support lists. */
  experimentItems: string[];
  submitting: boolean;
  onSubmit: (payload: RecipePayload) => void;
}) {
  const [form, setForm] = useState<FormState>(EMPTY);

  const set = (patch: Partial<FormState>) => setForm({ ...form, ...patch });

  const compatibleMachines = useMemo(
    () =>
      machines.filter((machine) =>
        machine.supportedItems.includes(form.experimentItem),
      ),
    [machines, form.experimentItem],
  );

  function submit() {
    // Prefer the chosen machine when it is compatible, otherwise fall back to
    // the first compatible machine (preserving the original page behavior).
    const machineId = compatibleMachines.some(
      (machine) => machine.machineId === form.machineId,
    )
      ? form.machineId
      : (compatibleMachines[0]?.machineId ?? form.machineId);

    onSubmit({
      recipeId: form.recipeId,
      name: form.name,
      version: form.version,
      experimentItem: form.experimentItem,
      machineIds: [machineId],
      method: form.method,
      parameters: parseParameters(form.parameters),
      updatedBy: form.updatedBy,
    });
  }

  return (
    <Panel
      title="新增 Recipe"
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
          placeholder="Recipe ID，例如 RCP-001"
          value={form.recipeId}
          onChange={(e) => set({ recipeId: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="Recipe 名稱"
          value={form.name}
          onChange={(e) => set({ name: e.target.value })}
          style={inputStyle}
        />
        <input
          placeholder="版本，例如 v1.0"
          value={form.version}
          onChange={(e) => set({ version: e.target.value })}
          style={inputStyle}
        />
        <select
          value={form.experimentItem}
          onChange={(e) =>
            set({ experimentItem: e.target.value, machineId: "" })
          }
          style={inputStyle}
        >
          <option value="">選擇實驗項目</option>
          {experimentItems.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          value={form.machineId}
          onChange={(e) => set({ machineId: e.target.value })}
          style={inputStyle}
        >
          <option value="">選擇相容機台</option>
          {(compatibleMachines.length ? compatibleMachines : machines).map(
            (machine) => (
              <option key={machine.machineId} value={machine.machineId}>
                {machine.machineId} · {machine.name} · {formatLab(machine.lab)}
              </option>
            ),
          )}
        </select>
        <textarea
          placeholder="實驗方法"
          value={form.method}
          onChange={(e) => set({ method: e.target.value })}
          style={{ ...inputStyle, minHeight: 90 }}
        />
        <input
          placeholder="參數 key:value，用逗號分隔"
          value={form.parameters}
          onChange={(e) => set({ parameters: e.target.value })}
          style={inputStyle}
        />
        <Btn variant="primary" disabled={submitting} onClick={submit}>
          {submitting ? "建立中…" : "建立 Recipe"}
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
