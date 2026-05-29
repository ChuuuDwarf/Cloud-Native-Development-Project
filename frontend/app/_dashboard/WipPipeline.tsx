"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { WipPipeline as WipPipelineData, Pair } from "@/types/dashboard";

type StageKey =
  | "waiting_dispatch"
  | "dispatched"
  | "in_progress"
  | "awaiting_handoff"
  | "done"
  | "terminated";

interface StageDef {
  key: StageKey;
  label: string;
  color: string;
  drillTo: string;
  // If set, the segment is filled with the SVG pattern of this id instead of
  // the solid color. Used for "terminated" so it visually reads as a
  // cancelled/abnormal state.
  patternId?: string;
}

const STAGES: StageDef[] = [
  {
    key: "waiting_dispatch",
    label: "待排程",
    color: "var(--text3)",
    drillTo: "/dispatch",
  },
  {
    key: "dispatched",
    label: "排程",
    color: "var(--cyan)",
    drillTo: "/dispatch",
  },
  {
    key: "in_progress",
    label: "進行",
    color: "var(--blue)",
    drillTo: "/execution",
  },
  {
    key: "awaiting_handoff",
    label: "待傳",
    color: "var(--orange)",
    drillTo: "/execution",
  },
  { key: "done", label: "完", color: "#3fb950", drillTo: "/storage" },
  {
    key: "terminated",
    label: "終止",
    color: "var(--red)",
    drillTo: "/orders?status=terminated",
    patternId: "wip-stripe-terminated",
  },
];

function Arrow({ delta }: { delta: number }) {
  if (delta > 0) return <span style={{ color: "#3fb950" }}>↑{delta}</span>;
  if (delta < 0) return <span style={{ color: "var(--red)" }}>↓{Math.abs(delta)}</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

interface PieDatum {
  key: StageKey;
  label: string;
  color: string;
  patternId?: string;
  value: number;
  delta: number;
  drillTo: string;
}

interface TooltipPayloadEntry {
  payload: PieDatum;
}

function PieTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  total: number;
}) {
  if (!active || !payload || payload.length === 0 || total === 0) return null;
  const datum = payload[0].payload;
  const pct = Math.round((datum.value / total) * 100);
  return (
    <div
      data-testid="wip-tooltip"
      style={{
        background: "#0a0a0a",
        color: "white",
        fontSize: 11,
        padding: "4px 8px",
        borderRadius: 4,
        fontFamily: "monospace",
        border: "1px solid var(--border)",
      }}
    >
      {datum.label} · {datum.value} · {pct}%
    </div>
  );
}

export default function WipPipeline({ data }: { data: WipPipelineData }) {
  const total = data.total;

  // Build pie data: keep every stage so the legend lists 6 rows, but the pie
  // itself drops zero-value entries (Recharts renders empty slices as a thin
  // visual artifact otherwise).
  const allStages: PieDatum[] = STAGES.map((s) => {
    const [value, delta] = data[s.key] as Pair;
    return {
      key: s.key,
      label: s.label,
      color: s.color,
      patternId: s.patternId,
      value,
      delta,
      drillTo: s.drillTo,
    };
  });
  const pieData = allStages.filter((d) => d.value > 0);

  return (
    <div
      data-testid="wip-pipeline"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14 }}>WIP pipeline</h3>
        <span
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          共 {total} 件
        </span>
      </div>

      {total === 0 ? (
        <div
          style={{
            background: "var(--s2)",
            borderRadius: 4,
            color: "var(--text3)",
            fontSize: 12,
            textAlign: "center",
            padding: 24,
          }}
        >
          目前無 WIP
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
            flex: 1,
            minHeight: 0,
          }}
        >
          {/* Donut. Wrapped so the center label can sit absolutely on top. */}
          <div
            data-testid="wip-donut"
            style={{
              position: "relative",
              minHeight: 180,
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                {/* SVG <defs> for the terminated stripe pattern. Recharts
                    passes raw children through to the SVG root, so this
                    becomes a real <defs> element on the page. */}
                <defs>
                  <pattern
                    id="wip-stripe-terminated"
                    patternUnits="userSpaceOnUse"
                    width="10"
                    height="10"
                    patternTransform="rotate(45)"
                  >
                    <rect width="6" height="10" fill="var(--red)" />
                    <rect x="6" width="4" height="10" fill="rgba(0,0,0,0.4)" />
                  </pattern>
                </defs>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="label"
                  innerRadius="60%"
                  outerRadius="100%"
                  paddingAngle={1}
                  stroke="var(--s1)"
                  strokeWidth={2}
                  isAnimationActive={false}
                  onClick={(entry: unknown) => {
                    const datum = entry as { payload?: PieDatum };
                    if (datum.payload?.drillTo) {
                      window.location.href = datum.payload.drillTo;
                    }
                  }}
                >
                  {pieData.map((d) => (
                    <Cell
                      key={d.key}
                      fill={
                        d.patternId ? `url(#${d.patternId})` : d.color
                      }
                      style={{ cursor: "pointer" }}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={<PieTooltip total={total} />}
                  wrapperStyle={{ outline: "none" }}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center label sits on top of the donut. pointerEvents: none so
                hover/click pass through to the underlying pie. */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                pointerEvents: "none",
              }}
            >
              <span
                data-testid="wip-donut-total"
                style={{
                  fontSize: 16,
                  fontFamily: "monospace",
                  color: "var(--text)",
                  fontWeight: 600,
                }}
              >
                共 {total} 件
              </span>
            </div>
          </div>

          {/* Side legend. One row per stage with colored dot, label, count,
              and 24h delta arrow. Clicking drills to the same path the
              segment uses. */}
          <div
            data-testid="wip-legend"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              fontSize: 12,
              justifyContent: "center",
            }}
          >
            {allStages.map((d) => (
              <button
                key={d.key}
                data-testid={`wip-legend-${d.key}`}
                onClick={() => {
                  window.location.href = d.drillTo;
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text2)",
                  cursor: "pointer",
                  textAlign: "left",
                  padding: "2px 0",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span
                  data-testid={`wip-legend-swatch-${d.key}`}
                  style={{
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: d.patternId
                      ? "repeating-linear-gradient(45deg, var(--red) 0 3px, rgba(0,0,0,0.4) 3px 5px)"
                      : d.color,
                    flexShrink: 0,
                  }}
                />
                <span style={{ color: "var(--text)", minWidth: 40 }}>
                  {d.label}
                </span>
                <span
                  style={{
                    color: "var(--text)",
                    fontFamily: "monospace",
                    minWidth: 24,
                    textAlign: "right",
                  }}
                >
                  {d.value}
                </span>
                <span style={{ fontSize: 11, fontFamily: "monospace" }}>
                  <Arrow delta={d.delta} />
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
