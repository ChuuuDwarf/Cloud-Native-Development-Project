"use client";

import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { DashboardMachine } from "@/types/dashboard";

export default function AttentionPanel({
  machines,
}: {
  machines: DashboardMachine[];
}) {
  return (
    <Panel title="需注意" tag={`${machines.length} 項`}>
      {machines.map((machine) => (
        <div
          key={machine.machineId}
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border2)",
            fontSize: 12,
          }}
        >
          <strong style={{ color: "var(--orange)" }}>
            {machine.machineId}
          </strong>
          <span style={{ color: "var(--text2)" }}>
            {" "}
            · {formatLab(machine.lab)} · {machine.status}
          </span>
        </div>
      ))}
      {machines.length === 0 && (
        <div style={{ padding: 16, color: "var(--text3)", fontSize: 12 }}>
          目前沒有故障、保養或停用機台。
        </div>
      )}
    </Panel>
  );
}
