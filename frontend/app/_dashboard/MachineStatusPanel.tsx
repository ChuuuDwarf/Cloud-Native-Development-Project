"use client";

import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { DashboardMachine } from "@/types/dashboard";

export default function MachineStatusPanel({
  machines,
}: {
  machines: DashboardMachine[];
}) {
  return (
    <Panel title="機台狀態" tag={`${machines.length} 台`}>
      {machines.slice(0, 8).map((machine) => (
        <div
          key={machine.machineId}
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border2)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 8,
            }}
          >
            <span style={{ fontFamily: "monospace", color: "var(--text)" }}>
              {machine.machineId}
            </span>
            <span
              style={{
                color:
                  machine.status === "閒置"
                    ? "var(--green)"
                    : machine.status === "使用中"
                      ? "var(--blue)"
                      : "var(--red)",
                fontSize: 11,
              }}
            >
              {machine.status}
            </span>
          </div>
          <div style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
            {formatLab(machine.lab)} · {machine.name}
          </div>
          <div
            style={{
              height: 5,
              background: "var(--s3)",
              borderRadius: 3,
              overflow: "hidden",
              marginTop: 8,
            }}
          >
            <div
              style={{
                width: `${machine.utilization}%`,
                height: "100%",
                background: "linear-gradient(90deg,var(--blue),var(--cyan))",
              }}
            />
          </div>
        </div>
      ))}
    </Panel>
  );
}
