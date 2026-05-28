"use client";

import type { LabRow } from "@/types/dashboard";

function Trend({ t }: { t: "up" | "flat" | "down" }) {
  if (t === "up") return <span style={{ color: "#3fb950" }}>↑</span>;
  if (t === "down") return <span style={{ color: "var(--red)" }}>↓</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
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
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>Lab Leaderboard</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>無 lab 資料</div>
      ) : (
        <ul
          style={{
            margin: 0,
            padding: 0,
            listStyle: "none",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {rows.map((r) => (
            <li
              key={r.lab_name}
              onClick={() => {
                window.location.href = `/orders?lab=${encodeURIComponent(r.lab_name)}`;
              }}
              style={{
                cursor: "pointer",
                display: "grid",
                gridTemplateColumns: "minmax(60px, 1fr) auto auto auto auto 20px",
                gap: 8,
                fontSize: 12,
                color: "var(--text2)",
                alignItems: "baseline",
              }}
            >
              <span style={{ fontFamily: "monospace" }}>{r.lab_name}</span>
              <span>完工 {r.completed_today}</span>
              <span>待傳 {r.awaiting_handoff}</span>
              <span>告警 {r.open_high_critical_issues}</span>
              <span style={{ fontFamily: "monospace" }}>util {r.avg_utilization_pct}%</span>
              <Trend t={r.trend_24h} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
