"use client";

import type { CompletionRow } from "@/types/dashboard";

function ago(iso: string): string {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m} min ago`;
  return `${Math.round(m / 60)} h ago`;
}

export default function CompletionsList({ rows }: { rows: CompletionRow[] }) {
  return (
    <div
      data-testid="completions-list"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>Recent Completions</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>近 30 分鐘無回傳</div>
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
              key={r.wip_no}
              onClick={() => {
                window.location.href = `/storage?order=${r.order_no}`;
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
              <span
                style={{
                  fontSize: 10,
                  background: "var(--s2)",
                  padding: "2px 6px",
                  borderRadius: 4,
                  color: "#3fb950",
                }}
              >
                完
              </span>
              <span
                style={{
                  fontFamily: "monospace",
                  color: "var(--text1)",
                }}
              >
                {r.wip_no}
              </span>
              <span
                style={{
                  fontFamily: "monospace",
                  color: "var(--text3)",
                }}
              >
                {r.order_no}
              </span>
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{ago(r.returned_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
