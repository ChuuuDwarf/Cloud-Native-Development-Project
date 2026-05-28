"use client";

import type { TriageItem } from "@/types/dashboard";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--red)",
  high: "var(--orange)",
  medium: "#d4a300",
  low: "var(--cyan)",
};

const TYPE_LABEL: Record<TriageItem["type"], string> = {
  pending_approval: "簽",
  escalated_issue: "升",
  open_issue: "告",
};

function TypeLabel({ type }: { type: TriageItem["type"] }) {
  return (
    <span
      style={{
        fontSize: 10,
        background: "var(--s2)",
        padding: "2px 6px",
        borderRadius: 4,
        color: "var(--text2)",
      }}
    >
      {TYPE_LABEL[type]}
    </span>
  );
}

function ago(iso: string): string {
  const diffMin = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (diffMin < 60) return `${diffMin} min ago`;
  return `${Math.round(diffMin / 60)} h ago`;
}

function drillTo(item: TriageItem): string {
  if (item.type === "pending_approval") return `/approve?order=${item.ref_id}`;
  return `/issues/${item.ref_id}`;
}

export default function TriageList({ items }: { items: TriageItem[] }) {
  return (
    <div
      data-testid="triage-list"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>待 triage</h3>
      {items.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>目前無待處理事項</div>
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
          {items.map((it) => (
            <li
              key={`${it.type}-${it.ref_id}`}
              onClick={() => {
                window.location.href = drillTo(it);
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
              <TypeLabel type={it.type} />
              {it.severity && (
                <span style={{ color: SEVERITY_COLOR[it.severity] }}>{it.severity}</span>
              )}
              {it.lab_name && (
                <span
                  style={{
                    fontFamily: "monospace",
                    color: "var(--text3)",
                  }}
                >
                  {it.lab_name}
                </span>
              )}
              <span
                style={{
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {it.label}
              </span>
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{ago(it.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
