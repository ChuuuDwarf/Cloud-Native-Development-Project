"use client";

import type { MachineHeatmap as MachineHeatmapData, MachineGrid } from "@/types/dashboard";

const STATUS_COLOR: Record<string, string> = {
  in_use: "var(--blue)",
  idle: "var(--text3)",
  maintenance: "var(--orange)",
  faulty: "var(--red)",
  disabled: "#3a3a3a",
};

function Tile({ m }: { m: MachineGrid }) {
  const isFaulty = m.status === "faulty";
  const tooltipParts: string[] = [m.machine_no, m.status];
  if (m.current_recipe) tooltipParts.push(`recipe ${m.current_recipe}`);
  if (m.current_operator) tooltipParts.push(`op ${m.current_operator}`);
  if (m.today_hours) tooltipParts.push(`${m.today_hours.toFixed(1)}h today`);
  return (
    <div
      title={tooltipParts.join(" · ")}
      style={{
        width: 28,
        height: 28,
        borderRadius: 4,
        background: STATUS_COLOR[m.status] || "var(--text3)",
        backgroundImage: isFaulty
          ? "repeating-linear-gradient(45deg, transparent 0 4px, rgba(0,0,0,0.4) 4px 6px)"
          : undefined,
        cursor: "pointer",
        flexShrink: 0,
      }}
      onClick={() => {
        window.location.href = `/machine?id=${m.machine_id}`;
      }}
    />
  );
}

export default function MachineHeatmap({
  data,
  showLabPrefix,
}: {
  data: MachineHeatmapData;
  showLabPrefix: boolean;
}) {
  const labKeys = Object.keys(data.by_lab).sort();
  return (
    <div
      data-testid="machine-heatmap"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14 }}>機台狀態</h3>
        <span
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          avg util {data.avg_utilization_pct}% · in_use {data.in_use_count}/{data.total_count}
        </span>
      </div>
      {data.total_count === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>無機台資料</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {labKeys.map((lab) => (
            <div key={lab} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {showLabPrefix && (
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--text3)",
                    fontFamily: "monospace",
                    width: 56,
                  }}
                >
                  {lab}
                </span>
              )}
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {data.by_lab[lab].map((m) => (
                  <Tile key={m.machine_id} m={m} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
