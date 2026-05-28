"use client";

import type { EscalationRow } from "@/types/dashboard";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--red)",
  high: "var(--orange)",
  medium: "#d4a300",
  low: "var(--cyan)",
};

function ago(iso: string): string {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m} min ago`;
  return `${Math.round(m / 60)} h ago`;
}

export default function EscalationsList({ rows }: { rows: EscalationRow[] }) {
  return (
    <div
      data-testid="escalations-list"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>Recent Escalations</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>過去 24h 無升級</div>
      ) : (
        <ul
          style={{
            margin: 0,
            padding: 0,
            listStyle: "none",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {rows.map((r) => (
            <li
              key={r.issue_id}
              onClick={() => {
                window.location.href = `/issues/${r.issue_id}`;
              }}
              style={{
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "var(--text2)",
              }}
            >
              <span style={{ color: SEVERITY_COLOR[r.severity] }}>{r.severity}</span>
              <span
                style={{
                  fontSize: 10,
                  color: "var(--text3)",
                  fontFamily: "monospace",
                }}
              >
                L{r.escalation_level}
              </span>
              <span
                style={{
                  fontFamily: "monospace",
                  color: "var(--text3)",
                }}
              >
                {r.lab_name}
              </span>
              <span
                style={{
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {r.title}
              </span>
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{ago(r.escalated_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
