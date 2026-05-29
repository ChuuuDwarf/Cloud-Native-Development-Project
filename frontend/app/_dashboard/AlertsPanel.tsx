"use client";

import type { EscalationRow, TriageItem } from "@/types/dashboard";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--red)",
  high: "var(--orange)",
  medium: "#d4a300",
  low: "var(--cyan)",
};

const MAX_ROWS = 7;

type AlertRow = {
  issue_id: string;
  lab_name: string | null;
  severity: string;
  title: string;
  escalation_level: number; // 0 when not escalated
  // ISO timestamp used for both display ("X min ago") and within-group recency sort.
  timestamp: string;
  acknowledged: boolean;
  // Priority group: lower = more urgent. Used to sort across groups.
  // 0: unack escalated, 1: unack critical, 2: unack high, 3: ack'd escalated (context)
  group: 0 | 1 | 2 | 3;
};

function ago(iso: string): string {
  const diffMin = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (diffMin < 60) return `${diffMin} min ago`;
  return `${Math.round(diffMin / 60)} h ago`;
}

/**
 * Merge unacknowledged high/critical issues with the recent-escalations list
 * into a single deduplicated, priority-sorted view.
 *
 * Priority groups (lower = more urgent):
 *   0 — unack escalated (in recent_escalations AND in unack list)
 *   1 — unack critical (in unack list, severity === "critical", not escalated)
 *   2 — unack high (in unack list, severity === "high", not escalated)
 *   3 — ack'd escalated (only in recent_escalations) — context only, dimmed
 *
 * Within each group: most recent first (created_at / escalated_at desc).
 * Dedup: same issue_id appears once; if it's in both lists, the unack entry
 * is the source of truth (richer data) but the escalation_level is preserved.
 */
function buildRows(
  unackHighCriticalIssues: TriageItem[],
  recentEscalations: EscalationRow[]
): AlertRow[] {
  const escalationsById = new Map<string, EscalationRow>();
  for (const e of recentEscalations) {
    escalationsById.set(e.issue_id, e);
  }

  const seen = new Set<string>();
  const merged: AlertRow[] = [];

  // First, walk the unack list (richer). These are NOT acknowledged.
  for (const item of unackHighCriticalIssues) {
    if (seen.has(item.ref_id)) continue;
    seen.add(item.ref_id);

    const matchingEsc = escalationsById.get(item.ref_id);
    const isEscalated = item.type === "escalated_issue" || (matchingEsc?.escalation_level ?? 0) > 0;
    const severity = item.severity ?? matchingEsc?.severity ?? "high";

    let group: AlertRow["group"];
    if (isEscalated) group = 0;
    else if (severity === "critical") group = 1;
    else group = 2;

    merged.push({
      issue_id: item.ref_id,
      lab_name: item.lab_name ?? matchingEsc?.lab_name ?? null,
      severity,
      title: item.label,
      escalation_level: matchingEsc?.escalation_level ?? (isEscalated ? 1 : 0),
      timestamp: matchingEsc?.escalated_at ?? item.created_at,
      acknowledged: false,
      group,
    });
  }

  // Then, walk recent_escalations to pick up ack'd-but-still-recent entries.
  for (const esc of recentEscalations) {
    if (seen.has(esc.issue_id)) continue;
    seen.add(esc.issue_id);

    merged.push({
      issue_id: esc.issue_id,
      lab_name: esc.lab_name,
      severity: esc.severity,
      title: esc.title,
      escalation_level: esc.escalation_level,
      timestamp: esc.escalated_at,
      acknowledged: true,
      group: 3,
    });
  }

  merged.sort((a, b) => {
    if (a.group !== b.group) return a.group - b.group;
    // Within group, most recent first.
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  return merged.slice(0, MAX_ROWS);
}

function SeverityBadge({ severity }: { severity: string }) {
  const color = SEVERITY_COLOR[severity] ?? "var(--text3)";
  return (
    <span
      style={{
        fontSize: 10,
        padding: "2px 6px",
        borderRadius: 4,
        background: "var(--s2)",
        color,
        fontFamily: "monospace",
        textTransform: "uppercase",
        letterSpacing: 0.5,
        flexShrink: 0,
        minWidth: 56,
        textAlign: "center",
      }}
    >
      {severity}
    </span>
  );
}

export interface AlertsPanelProps {
  unackHighCriticalIssues: TriageItem[];
  recentEscalations: EscalationRow[];
}

export default function AlertsPanel({
  unackHighCriticalIssues,
  recentEscalations,
}: AlertsPanelProps) {
  const rows = buildRows(unackHighCriticalIssues, recentEscalations);

  return (
    <div
      data-testid="alerts-panel"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>異常警報</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>目前無未處理異常</div>
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
              data-testid="alerts-panel-row"
              data-issue-id={r.issue_id}
              data-acknowledged={r.acknowledged ? "true" : "false"}
              data-group={r.group}
              onClick={() => {
                window.location.href = `/issues/${r.issue_id}`;
              }}
              style={{
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                color: "var(--text2)",
                opacity: r.acknowledged ? 0.55 : 1,
              }}
            >
              <SeverityBadge severity={r.severity} />
              {r.lab_name && (
                <span
                  style={{
                    fontFamily: "monospace",
                    color: "var(--text3)",
                    width: 56,
                    flexShrink: 0,
                  }}
                >
                  {r.lab_name}
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
                {r.title}
                {r.acknowledged && (
                  <span style={{ color: "var(--text3)", marginLeft: 6 }}>(ack)</span>
                )}
              </span>
              {r.escalation_level > 0 && (
                <span
                  style={{
                    fontSize: 10,
                    color: "var(--text3)",
                    fontFamily: "monospace",
                    flexShrink: 0,
                  }}
                >
                  L{r.escalation_level}
                </span>
              )}
              <span style={{ fontSize: 10, color: "var(--text3)", flexShrink: 0 }}>
                {ago(r.timestamp)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
