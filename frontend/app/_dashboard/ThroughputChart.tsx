"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ThroughputPoint } from "@/types/dashboard";

// hour_offset 0..23. Backend bucket origin is
// ``(now - 23h).replace(minute=0, ...)`` so bucket 23 covers the current
// hour, and bucket 0 starts at the top-of-hour 23h before now.
// Label maps offset n → wall-clock hour `(nowHour + n - 23) mod 24`:
//   n=23 → nowHour (current hour)
//   n=0  → (nowHour - 23) mod 24 = (nowHour + 1) mod 24
export function formatHourLabel(offset: unknown): string {
  const n = typeof offset === "number" ? offset : Number(offset);
  if (!Number.isFinite(n)) return "";
  const nowHour = new Date().getHours();
  const actualHour = (((nowHour + n - 23) % 24) + 24) % 24;
  return `${String(actualHour).padStart(2, "0")}:00`;
}

export default function ThroughputChart({ data }: { data: ThroughputPoint[] }) {
  const empty =
    data.length === 0 || data.every((p) => p.completed === 0 && p.returned === 0);

  const sumCompleted = data.reduce((acc, p) => acc + p.completed, 0);
  const sumReturned = data.reduce((acc, p) => acc + p.returned, 0);

  return (
    <div
      data-testid="throughput-chart"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
        display: "flex",
        flexDirection: "column",
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
        <h3 style={{ margin: 0, fontSize: 14 }}>24h 產出趨勢</h3>
        <span
          data-testid="throughput-totals"
          style={{ fontSize: 11, color: "var(--text3)", fontFamily: "monospace" }}
        >
          完工 {sumCompleted} · 回傳 {sumReturned}
        </span>
      </div>
      {empty ? (
        <div
          data-testid="throughput-empty"
          style={{
            flex: 1,
            background: "var(--s2)",
            borderRadius: 4,
            color: "var(--text3)",
            fontSize: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 160,
          }}
        >
          近 24h 無產出
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 160, height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 8, right: 8, bottom: 24, left: 0 }}
            >
              <CartesianGrid strokeDasharray="2 4" opacity={0.15} />
              <XAxis
                dataKey="hour_offset"
                tickFormatter={formatHourLabel}
                angle={-45}
                textAnchor="end"
                interval={0}
                tick={{ fontSize: 10, fontFamily: "monospace", fill: "var(--text3)" }}
                height={40}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 10, fontFamily: "monospace", fill: "var(--text3)" }}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  background: "#0a0a0a",
                  border: "none",
                  borderRadius: 4,
                  padding: "4px 8px",
                }}
                labelStyle={{ color: "white", fontSize: 11 }}
                itemStyle={{ fontSize: 11 }}
                labelFormatter={formatHourLabel}
              />
              <Line
                type="monotone"
                dataKey="completed"
                name="完工"
                stroke="var(--blue)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3 }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="returned"
                name="回傳"
                stroke="#3fb950"
                strokeWidth={2}
                strokeDasharray="4 3"
                dot={false}
                activeDot={{ r: 3 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
