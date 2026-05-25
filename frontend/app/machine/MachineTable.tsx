"use client";

import Btn from "@/components/ui/Btn";
import Chip from "@/components/ui/Chip";
import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { Machine, MachineStatus } from "@/types/machines";

type ChipType = "idle" | "running" | "pending" | "rejected";

const STATUS_CHIP: Record<MachineStatus, ChipType> = {
  閒置: "idle",
  使用中: "running",
  保養中: "pending",
  故障中: "rejected",
  停用: "rejected",
};

const HEADERS = [
  "機台",
  "實驗室",
  "狀態",
  "支援項目",
  "稼動率",
  "保養日",
  "操作",
];

export default function MachineTable({
  machines,
  applyLabel,
  applying,
  onEdit,
  onApplyStatus,
}: {
  machines: Machine[];
  /** Label of the status that the "套用狀態" button will apply. */
  applyLabel: string;
  applying: boolean;
  onEdit: (machine: Machine) => void;
  onApplyStatus: (machineId: string) => void;
}) {
  return (
    <Panel title="機台清單" tag={`${machines.length} 筆`}>
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
          {machines.map((machine) => (
            <tr
              key={machine.machineId}
              style={{ borderBottom: "1px solid var(--border2)" }}
            >
              <td style={tdStyle}>
                <div style={{ fontFamily: "monospace", color: "var(--text)" }}>
                  {machine.machineId}
                </div>
                <div style={{ color: "var(--text3)", fontSize: 11 }}>
                  {machine.name} · {machine.owner}
                </div>
              </td>
              <td style={tdStyle}>{formatLab(machine.lab)}</td>
              <td style={tdStyle}>
                <Chip
                  type={STATUS_CHIP[machine.status]}
                  label={machine.status}
                />
              </td>
              <td style={tdStyle}>{machine.supportedItems.join("、")}</td>
              <td style={tdStyle}>{machine.utilization}%</td>
              <td style={tdStyle}>{machine.lastMaintenance}</td>
              <td style={tdStyle}>
                <div style={{ display: "flex", gap: 6 }}>
                  <Btn small onClick={() => onEdit(machine)}>
                    編輯
                  </Btn>
                  <Btn
                    small
                    variant="primary"
                    disabled={applying}
                    onClick={() => onApplyStatus(machine.machineId)}
                    title={`套用狀態：${applyLabel}`}
                  >
                    套用狀態
                  </Btn>
                </div>
              </td>
            </tr>
          ))}
          {machines.length === 0 && (
            <tr>
              <td
                colSpan={HEADERS.length}
                style={{ ...tdStyle, textAlign: "center", padding: 28 }}
              >
                尚無機台，請先從左側新增。
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
