"use client";

import {
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
} from "recharts";

import type { MachineHeatmap as MachineHeatmapData, MachineGrid } from "@/types/dashboard";

const STATUS_COLOR: Record<string, string> = {
  in_use: "var(--blue)",
  idle: "var(--text3)",
  maintenance: "var(--orange)",
  faulty: "var(--red)",
  disabled: "#3a3a3a",
};

// Spec section 2 threshold colors (also used by per-lab mini util bars).
function utilColor(pct: number): string {
  if (pct >= 95) return "var(--red)";
  if (pct >= 80) return "var(--orange)";
  if (pct >= 40) return "var(--blue)";
  return "var(--text3)";
}

const MINI_BAR_WIDTH = 20;

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

function RadialGauge({
  pct,
  color,
  size = 240,
}: {
  pct: number;
  color: string;
  size?: number;
}) {
  // Single semicircle bar showing `pct` out of 100. The background prop
  // renders the unused portion as a grey track. ``size`` scales the whole
  // gauge — inner value/caption follow.
  const data = [{ name: "util", value: pct, fill: color }];
  const valueFont = Math.max(40, Math.round(size * 0.27));
  const captionFont = Math.max(12, Math.round(size * 0.06));
  return (
    <div
      data-testid="radial-gauge"
      data-util-color={color}
      style={{ width: size, height: size / 1.6, position: "relative" }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          data={data}
          startAngle={180}
          endAngle={0}
          innerRadius="60%"
          outerRadius="100%"
          cx="50%"
          cy="100%"
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar
            dataKey="value"
            cornerRadius={6}
            background={{ fill: "var(--s2)" }}
            isAnimationActive={false}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "flex-end",
          paddingBottom: Math.round(size * 0.04),
          pointerEvents: "none",
        }}
      >
        <span style={{ fontSize: valueFont, fontWeight: 700, color, lineHeight: 1 }}>{pct}%</span>
        <span
          style={{
            fontSize: captionFont,
            fontFamily: "monospace",
            color: "var(--text3)",
            marginTop: 2,
          }}
        >
          avg util
        </span>
      </div>
    </div>
  );
}

function LabUtilMiniBar({ pct }: { pct: number }) {
  const color = utilColor(pct);
  const fillPx = Math.round((pct / 100) * MINI_BAR_WIDTH);
  return (
    <div
      data-testid="lab-mini-util"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        gap: 2,
      }}
    >
      <span style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text3)" }}>{pct}%</span>
      <div
        style={{
          width: MINI_BAR_WIDTH,
          height: 8,
          background: "var(--s2)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          data-testid="lab-mini-util-fill"
          data-fill-px={fillPx}
          style={{
            width: fillPx,
            height: "100%",
            background: color,
          }}
        />
      </div>
    </div>
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
  const avg = data.avg_utilization_pct;
  const avgColor = utilColor(avg);
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
          alignItems: "baseline",
          marginBottom: 8,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14 }}>機台狀態</h3>
        <span
          style={{
            fontSize: 12,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          in_use {data.in_use_count}/{data.total_count}
        </span>
      </div>
      {/* Hero gauge — dominates the panel per user request "fill 80% of widget". */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <RadialGauge pct={avg} color={avgColor} size={360} />
      </div>
      {data.total_count === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>無機台資料</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {labKeys.map((lab) => {
            const labUtil = data.per_lab_util_pct?.[lab];
            return (
              <div
                key={lab}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
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
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", flex: 1 }}>
                  {data.by_lab[lab].map((m) => (
                    <Tile key={m.machine_id} m={m} />
                  ))}
                </div>
                {labUtil !== undefined && <LabUtilMiniBar pct={labUtil} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
