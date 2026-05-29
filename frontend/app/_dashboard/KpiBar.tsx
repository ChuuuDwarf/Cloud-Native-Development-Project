"use client";

import type { KpiBar as KpiBarData, KpiCardData } from "@/types/dashboard";

const COLOR_BY_THRESHOLD: Record<string, string> = {
  neutral: "var(--text2)",
  orange: "var(--orange)",
  red: "var(--red)",
};

const TILE_LABELS: Record<keyof KpiBarData, { label: string; drillTo: string }> = {
  new_orders: { label: "新單", drillTo: "/orders?created=today" },
  completed: { label: "完工", drillTo: "/execution?status=completed" },
  returned: { label: "回傳", drillTo: "/storage?status=returned" },
  pending_approval: { label: "待簽", drillTo: "/approve" },
  open_critical_high_issues: {
    label: "告警",
    drillTo: "/issues?severity=high,critical&status=open",
  },
};

function Arrow({ delta }: { delta: number }) {
  if (delta > 0) return <span style={{ color: "#3fb950" }}>↑{delta}</span>;
  if (delta < 0) return <span style={{ color: "var(--red)" }}>↓{Math.abs(delta)}</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

function Tile({ card, label, onClick }: { card: KpiCardData; label: string; onClick: () => void }) {
  const color = COLOR_BY_THRESHOLD[card.threshold_color] || "var(--text1)";
  return (
    <button
      onClick={onClick}
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        cursor: "pointer",
        textAlign: "left",
        height: 80,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div style={{ fontSize: 12, color: "var(--text2)" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color }}>{card.value}</span>
        <span style={{ fontSize: 11, fontFamily: "monospace" }}>
          <Arrow delta={card.delta_24h} />
        </span>
      </div>
    </button>
  );
}

export default function KpiBar({ data }: { data: KpiBarData }) {
  const handle = (path: string) => () => {
    window.location.href = path;
  };
  const entries = Object.entries(TILE_LABELS) as [
    keyof KpiBarData,
    { label: string; drillTo: string },
  ][];
  return (
    <div
      data-testid="kpi-bar"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: 14,
      }}
    >
      {entries.map(([key, { label, drillTo }]) => (
        <Tile key={key} card={data[key]} label={label} onClick={handle(drillTo)} />
      ))}
    </div>
  );
}
