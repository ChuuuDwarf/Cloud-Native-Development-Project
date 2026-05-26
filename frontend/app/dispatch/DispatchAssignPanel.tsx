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
  machineHint,
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
  machineHint?: string | null;
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
            .join("、") ||
            machineHint ||
            "無可用機台"}
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
        {activeDispatch?.status === "待派工" ? (
          <>
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
          </>
        ) : activeDispatch?.status === "待上機" ? (
          <div style={{ fontSize: 12, color: "var(--green)" }}>
            ✅ 已完成派工，請至「實驗執行」頁對該 WIP 上機。
          </div>
        ) : activeDispatch?.status === "待排程" ? (
          <div style={{ fontSize: 12, color: "var(--text3)" }}>
            尚未排程。請先按右上「產生建議」，進入「待派工」後才能確認派工。
          </div>
        ) : (
          <div style={{ fontSize: 12, color: "var(--text3)" }}>
            請從中間清單選一筆「待派工」的派工單。
          </div>
        )}
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
  // Without these the 100% width + padding (content-box) and the datetime-local
  // input's intrinsic min-width overflow the fixed-width (340px) right panel.
  boxSizing: "border-box",
  minWidth: 0,
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
