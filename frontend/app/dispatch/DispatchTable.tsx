"use client";

import Chip from "@/components/ui/Chip";
import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { Dispatch, WipStatus } from "@/types/dispatches";

const STATUS_CHIP: Record<WipStatus, "pending" | "review" | "approved"> = {
  待排程: "pending",
  待派工: "review",
  待上機: "approved",
};

const HEADERS = [
  "WIP",
  "實驗室",
  "實驗項目",
  "優先",
  "交期",
  "狀態",
  "建議 / 指派",
  "系統預估",
  "重排 / 策略",
];

export default function DispatchTable({
  dispatches,
  activeDispatchId,
  onSelect,
}: {
  dispatches: Dispatch[];
  activeDispatchId: string;
  onSelect: (dispatchId: string) => void;
}) {
  return (
    <Panel title="待排程 / 待排程清單" tag={`${dispatches.length} 筆`}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--s2)" }}>
            {HEADERS.map((header) => (
              <th key={header} style={thStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dispatches.map((dispatch) => (
            <tr
              key={dispatch.dispatchId}
              onClick={() => onSelect(dispatch.dispatchId)}
              style={{
                borderBottom: "1px solid var(--border2)",
                background:
                  activeDispatchId === dispatch.dispatchId
                    ? "rgba(56,139,253,0.08)"
                    : "transparent",
                cursor: "pointer",
              }}
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
              <td style={tdStyle}>{dispatch.dueAt}</td>
              <td style={tdStyle}>
                <Chip
                  type={STATUS_CHIP[dispatch.status]}
                  label={dispatch.status}
                />
              </td>
              <td style={tdStyle}>
                {dispatch.assignedMachineId ??
                  dispatch.suggestedMachineId ??
                  "尚未產生"}
              </td>
              <td style={tdStyle}>
                {dispatch.scheduledStart ?? "-"}
                <br />
                <span style={{ color: "var(--text3)" }}>
                  {dispatch.scheduledEnd ?? ""}
                </span>
              </td>
              <td style={tdStyle}>
                {dispatch.replanReason ?? "-"}
                <br />
                <span style={{ color: "var(--text3)" }}>
                  {dispatch.strategy ?? ""}
                </span>
              </td>
            </tr>
          ))}
          {dispatches.length === 0 && (
            <tr>
              <td
                colSpan={HEADERS.length}
                style={{ ...tdStyle, textAlign: "center", padding: 28 }}
              >
                尚無 WIP，請從左側新增。
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </Panel>
  );
}

const thStyle: React.CSSProperties = {
  fontSize: 10,
  letterSpacing: 1.5,
  color: "var(--text3)",
  padding: "10px 16px",
  textAlign: "left",
  fontFamily: "monospace",
  borderBottom: "1px solid var(--border2)",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 16px",
  fontSize: 12.5,
  color: "var(--text2)",
  verticalAlign: "middle",
};
