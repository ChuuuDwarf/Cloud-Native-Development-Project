"use client";

import Chip from "@/components/ui/Chip";
import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { DashboardDispatch } from "@/types/dashboard";
import type { WipStatus } from "@/types/dispatches";

const STATUS_CHIP: Record<WipStatus, "pending" | "review" | "approved"> = {
  待派工: "pending",
  排程中: "review",
  待上機: "approved",
};

const HEADERS = ["WIP", "LAB", "實驗項目", "優先", "狀態", "機台", "預估時間"];

export default function DispatchPanel({
  dispatches,
}: {
  dispatches: DashboardDispatch[];
}) {
  return (
    <Panel title="WIP 進度追蹤" tag={`${dispatches.length} 筆`}>
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
          {dispatches.slice(0, 8).map((dispatch) => (
            <tr
              key={dispatch.dispatchId}
              style={{ borderBottom: "1px solid var(--border2)" }}
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
              <td style={tdStyle}>
                <Chip
                  type={STATUS_CHIP[dispatch.status]}
                  label={dispatch.status}
                />
              </td>
              <td style={tdStyle}>{dispatch.suggestedMachineId ?? "-"}</td>
              <td style={tdStyle}>
                {dispatch.scheduledStart ?? "-"}
                <br />
                <span style={{ color: "var(--text3)" }}>
                  {dispatch.scheduledEnd ?? ""}
                </span>
              </td>
            </tr>
          ))}
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
