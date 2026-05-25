"use client";

import Panel from "@/components/ui/Panel";
import { formatLab } from "@/components/labDisplay";
import type { DashboardLab } from "@/types/dashboard";

export default function LabsPanel({
  labs,
  isGlobalView,
}: {
  labs: DashboardLab[];
  isGlobalView: boolean;
}) {
  return (
    <Panel
      title={isGlobalView ? "各 LAB 情況" : "本 LAB 情況"}
      tag={`${labs.length} LAB`}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3,1fr)",
          gap: 12,
          padding: 16,
        }}
      >
        {labs.map((lab) => (
          <div key={lab.lab} style={labCardStyle}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <strong>{formatLab(lab.lab)}</strong>
              <span style={badgeStyle}>{lab.avgUtilization}%</span>
            </div>
            <Metric label="WIP" value={lab.dispatchCount} />
            <Metric label="待派工" value={lab.pendingCount} />
            <Metric label="排程中" value={lab.schedulingCount} />
            <Metric
              label="不可用機台"
              value={lab.blockedMachineCount}
              danger={lab.blockedMachineCount > 0}
            />
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Metric({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: number;
  danger?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        color: "var(--text2)",
        fontSize: 12,
        marginTop: 6,
      }}
    >
      <span>{label}</span>
      <strong style={{ color: danger ? "var(--red)" : "var(--text)" }}>
        {value}
      </strong>
    </div>
  );
}

const badgeStyle: React.CSSProperties = {
  fontSize: 10,
  fontFamily: "monospace",
  color: "var(--text3)",
  background: "var(--s3)",
  padding: "2px 7px",
  borderRadius: 4,
};

const labCardStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 8,
  padding: 14,
};
