"use client";

import { Line, LineChart, ResponsiveContainer } from "recharts";

import type { KpiBar as KpiBarData, KpiCardData } from "@/types/dashboard";

const COLOR_BY_THRESHOLD: Record<string, string> = {
  neutral: "var(--text2)",
  orange: "var(--orange)",
  red: "var(--red)",
};

/**
 * Sparkline stroke is rendered at 0.15 opacity, which makes ``var(--text2)``
 * (the neutral KPI accent) invisible against ``var(--s1)`` dark surface.
 * Most flow KPIs have no threshold and would otherwise never show a
 * sparkline, so override neutral with ``var(--blue)`` for the spark layer
 * only — the tile's main number color stays neutral.
 */
const SPARKLINE_COLOR_BY_THRESHOLD: Record<string, string> = {
  neutral: "var(--blue)",
  orange: "var(--orange)",
  red: "var(--red)",
};

const TILE_LABELS: Record<keyof KpiBarData, { label: string; drillTo: string }> = {
  new_orders: { label: "新單", drillTo: "/approve" },
  completed: { label: "完工", drillTo: "/execution" },
  returned: { label: "回傳", drillTo: "/report" },
  pending_approval: { label: "待簽", drillTo: "/approve" },
  open_critical_high_issues: { label: "告警", drillTo: "/issues" },
};

function Arrow({ delta }: { delta: number }) {
  if (delta > 0) return <span style={{ color: "#3fb950" }}>↑{delta}</span>;
  if (delta < 0) return <span style={{ color: "var(--red)" }}>↓{Math.abs(delta)}</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

function TileSparkline({ series, color }: { series: number[] | null; color: string }) {
  // Skip render when no history is available or every bucket is zero.
  if (series == null || series.every((v) => v === 0)) return null;
  const data = series.map((v) => ({ v }));
  return (
    <div
      data-testid="kpi-sparkline"
      data-stroke={color}
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: "50%",
        pointerEvents: "none",
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeOpacity={0.15}
            strokeWidth={1.5}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Tile({ card, label, onClick }: { card: KpiCardData; label: string; onClick: () => void }) {
  const color = COLOR_BY_THRESHOLD[card.threshold_color] || "var(--text1)";
  const sparklineColor = SPARKLINE_COLOR_BY_THRESHOLD[card.threshold_color] || color;
  return (
    <button
      onClick={onClick}
      style={{
        position: "relative",
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
        overflow: "hidden",
      }}
    >
      <TileSparkline series={card.sparkline_24h} color={sparklineColor} />
      <div style={{ fontSize: 12, color: "var(--text2)", position: "relative", zIndex: 1 }}>
        {label}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          position: "relative",
          zIndex: 1,
        }}
      >
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
