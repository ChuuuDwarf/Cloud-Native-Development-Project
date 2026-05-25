"use client";

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import type { Machine } from "@/types/machines";
import type { Dispatch } from "@/types/dispatches";
import type { Recipe } from "@/types/recipes";

export default function DispatchAssignPanel({
  activeDispatch,
  assignableMachines,
  assignableRecipes,
  scheduledStart,
  scheduledEnd,
  canApplySuggested,
  canAssign,
  assigning,
  onScheduleChange,
  onApplySuggested,
  onAssign,
}: {
  activeDispatch?: Dispatch;
  assignableMachines: Machine[];
  assignableRecipes: Recipe[];
  scheduledStart: string;
  scheduledEnd: string;
  canApplySuggested: boolean;
  canAssign: boolean;
  assigning: boolean;
  onScheduleChange: (
    field: "scheduledStart" | "scheduledEnd",
    value: string,
  ) => void;
  onApplySuggested: () => void;
  onAssign: () => void;
}) {
  return (
    <Panel title="手動確認派工" tag={activeDispatch?.wipId ?? "N/A"}>
      <div
        style={{
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div style={fieldLabelStyle}>實驗項目</div>
        <div style={summaryBoxStyle}>
          {activeDispatch?.experimentItem ?? "未選擇 WIP"}
        </div>
        <div style={fieldLabelStyle}>可派工機台</div>
        <div style={summaryBoxStyle}>
          {assignableMachines
            .map((machine) => `${machine.machineId} ${machine.name}`)
            .join("、") || "無可用機台"}
        </div>
        <div style={fieldLabelStyle}>相容 Recipe</div>
        <div style={summaryBoxStyle}>
          {assignableRecipes
            .map((recipe) => `${recipe.recipeId} ${recipe.name}`)
            .join("、") || "無相容 Recipe"}
        </div>
        <div style={fieldLabelStyle}>最終派工時間</div>
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}
        >
          <input
            type="datetime-local"
            value={scheduledStart}
            onChange={(e) => onScheduleChange("scheduledStart", e.target.value)}
            style={inputStyle}
          />
          <input
            type="datetime-local"
            value={scheduledEnd}
            onChange={(e) => onScheduleChange("scheduledEnd", e.target.value)}
            style={inputStyle}
          />
        </div>
        <Btn small disabled={!canApplySuggested} onClick={onApplySuggested}>
          套用系統預估時間
        </Btn>
        <Btn
          variant="primary"
          disabled={!canAssign || assigning}
          onClick={onAssign}
        >
          {assigning ? "派工中…" : "確認派工"}
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

const fieldLabelStyle: React.CSSProperties = {
  fontSize: 10,
  letterSpacing: 1.5,
  color: "var(--text3)",
  fontFamily: "monospace",
};

const summaryBoxStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  color: "var(--text2)",
  padding: 10,
  borderRadius: 8,
  fontSize: 12,
  minHeight: 38,
};
