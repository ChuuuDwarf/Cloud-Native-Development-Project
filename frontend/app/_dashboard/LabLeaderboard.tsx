"use client";

import { Bar, BarChart, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { LabRow } from "@/types/dashboard";

type MetricKey =
  | "completed_today"
  | "awaiting_handoff"
  | "open_high_critical_issues"
  | "avg_utilization_pct";

interface SubChartSpec {
  metric: MetricKey;
  title: string;
  colorLabel: string;
  fill: string;
  sort: "asc" | "desc";
  suffix?: string;
}

/** Build the drill-down URL for a lab row. Exported for unit testing. */
export function buildLabDrillUrl(labName: string): string {
  return `/orders?lab=${encodeURIComponent(labName)}`;
}

/**
 * Recharts v3 wraps the row in a ``{ payload }`` envelope when invoking
 * ``Bar.onClick(data, index, event)``. Pull ``lab_name`` out defensively
 * so a shape change doesn't crash the dashboard.
 */
export function extractLabNameFromBarClick(arg: unknown): string | null {
  if (!arg || typeof arg !== "object") return null;
  const payload = (arg as { payload?: unknown }).payload;
  if (!payload || typeof payload !== "object") return null;
  const lab = (payload as { lab_name?: unknown }).lab_name;
  return typeof lab === "string" && lab.length > 0 ? lab : null;
}

const SUB_CHARTS: SubChartSpec[] = [
  {
    metric: "completed_today",
    title: "完工",
    colorLabel: "綠",
    fill: "#3fb950",
    sort: "desc",
  },
  {
    metric: "awaiting_handoff",
    title: "待傳",
    colorLabel: "橙",
    fill: "var(--orange)",
    sort: "desc",
  },
  {
    metric: "open_high_critical_issues",
    title: "告警",
    colorLabel: "紅",
    fill: "var(--red)",
    sort: "asc",
  },
  {
    metric: "avg_utilization_pct",
    title: "util%",
    colorLabel: "藍",
    fill: "var(--blue)",
    sort: "desc",
    suffix: "%",
  },
];

function SubChart({ rows, spec }: { rows: LabRow[]; spec: SubChartSpec }) {
  const sorted = [...rows].sort((a, b) => {
    const av = a[spec.metric];
    const bv = b[spec.metric];
    return spec.sort === "asc" ? av - bv : bv - av;
  });
  const allZero = sorted.every((r) => r[spec.metric] === 0);
  const suffix = spec.suffix ?? "";

  return (
    <div
      data-testid={`lab-subchart-${spec.metric}`}
      data-sort={spec.sort}
      data-order={sorted.map((r) => r.lab_name).join(",")}
      style={{ display: "flex", flexDirection: "column", height: "100%", minWidth: 0 }}
    >
      <h4
        style={{
          margin: 0,
          marginBottom: 6,
          fontSize: 11,
          fontFamily: "monospace",
          color: "var(--text2)",
          fontWeight: 600,
        }}
      >
        {spec.title}({spec.colorLabel})
      </h4>
      <div style={{ flex: 1, minHeight: 0 }}>
        {allZero ? (
          <div
            data-testid={`lab-subchart-empty-${spec.metric}`}
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text3)",
              fontSize: 14,
            }}
          >
            —
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={sorted}
              layout="vertical"
              margin={{ top: 0, right: 28, bottom: 0, left: 0 }}
            >
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="lab_name"
                width={56}
                tick={{ fontSize: 10, fontFamily: "monospace", fill: "var(--text2)" }}
                axisLine={false}
                tickLine={false}
              />
              <Bar
                dataKey={spec.metric}
                fill={spec.fill}
                isAnimationActive={false}
                onClick={(arg) => {
                  const lab = extractLabNameFromBarClick(arg);
                  if (lab) {
                    window.location.href = buildLabDrillUrl(lab);
                  }
                }}
                style={{ cursor: "pointer" }}
              >
                <LabelList
                  dataKey={spec.metric}
                  position="right"
                  style={{ fontSize: 11, fontFamily: "monospace", fill: "var(--text1)" }}
                  formatter={(v) => `${v}${suffix}`}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

export default function LabLeaderboard({ rows }: { rows: LabRow[] }) {
  return (
    <div
      data-testid="lab-leaderboard"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>無 lab 資料</div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
            flex: 1,
            minHeight: 0,
          }}
        >
          {SUB_CHARTS.map((spec) => (
            <SubChart key={spec.metric} rows={rows} spec={spec} />
          ))}
        </div>
      )}
    </div>
  );
}
