"use client";

import { useQuery } from "@tanstack/react-query";
import KpiCard from "@/components/ui/KpiCard";
import { PermissionGuard } from "@/components/PermissionGuard";
import { type Severity } from "@/constants/enums";
import { SeverityLabel } from "@/constants/status-labels";
import { dashboardApi } from "@/services/dashboard-api";
import type { LabBreakdown, RecentEscalation } from "@/types/dashboard";

export default function DashboardPage() {
  return (
    <PermissionGuard requiredPermission="dashboard:read">
      <DashboardContent />
    </PermissionGuard>
  );
}

function DashboardContent() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.getSnapshot(),
    refetchInterval: 30_000, // soft polling — dashboard isn't real-time critical
  });

  if (isLoading) {
    return <div style={{ padding: 24, color: "var(--text2)" }}>載入中…</div>;
  }
  if (isError) {
    return (
      <div style={{ padding: 24, color: "var(--red)" }}>
        儀表板載入失敗：{(error as Error).message}
      </div>
    );
  }
  if (!data) return null;

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, margin: 0 }}>
          主管儀表板
        </h1>
        <p
          style={{
            fontSize: 12,
            color: "var(--text3)",
            marginTop: 4,
            fontFamily: "monospace",
          }}
        >
          SUPERVISOR DASHBOARD · 自動每 30 秒更新
        </p>
      </div>

      {/* KPI grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 14,
          marginBottom: 24,
        }}
      >
        <KpiCard
          label="未結 issue 總數"
          value={data.issues.totalOpen}
          sub={`今日新增 ${data.issues.createdToday}`}
          color="var(--blue)"
          icon="📋"
        />
        <KpiCard
          label="今日升級"
          value={data.issues.escalatedToday}
          sub="status = escalated"
          color="var(--red)"
          icon="🚨"
        />
        <KpiCard
          label="High / Critical"
          value={(data.issues.bySeverity.high ?? 0) + (data.issues.bySeverity.critical ?? 0)}
          sub={`critical ${data.issues.bySeverity.critical ?? 0}`}
          color="var(--orange)"
          icon="⚠️"
        />
        <KpiCard
          label="您的未讀通知"
          value={data.unreadNotifications}
          sub="個人 inbox"
          color="var(--cyan)"
          icon="🔔"
        />
      </div>

      {/* Severity breakdown row */}
      <SeverityBar bySeverity={data.issues.bySeverity} />

      {/* Two columns: lab leaderboard + recent escalations */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginTop: 24,
        }}
      >
        <LabBreakdownPanel rows={data.byLab} />
        <RecentEscalationsPanel rows={data.recentEscalations} />
      </div>
    </div>
  );
}

function SeverityBar({ bySeverity }: { bySeverity: Record<string, number> }) {
  const order: { key: Severity; color: string; label: string }[] = [
    { key: "critical", color: "var(--red)", label: SeverityLabel.critical },
    { key: "high", color: "var(--orange)", label: SeverityLabel.high },
    { key: "medium", color: "var(--blue)", label: SeverityLabel.medium },
    { key: "low", color: "var(--text3)", label: SeverityLabel.low },
  ];
  const total = order.reduce((sum, s) => sum + (bySeverity[s.key] ?? 0), 0);
  return (
    <div
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div style={{ fontSize: 13, color: "var(--text2)", marginBottom: 10 }}>
        各 Severity 開立中數量 (total {total})
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {order.map((s) => (
          <span
            key={s.key}
            style={{
              background: s.color,
              color: "#fff",
              padding: "4px 12px",
              borderRadius: 16,
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            {s.label}: {bySeverity[s.key] ?? 0}
          </span>
        ))}
      </div>
    </div>
  );
}

function LabBreakdownPanel({ rows }: { rows: LabBreakdown[] }) {
  return (
    <div
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 12 }}>各實驗室 issue 狀態</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>沒有可顯示的實驗室。</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <Th>實驗室</Th>
              <Th align="right">未結</Th>
              <Th align="right">升級中</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.labId} style={{ borderBottom: "1px solid var(--border2)" }}>
                <Td>
                  <span style={{ fontFamily: "monospace" }}>{r.labCode}</span>
                  <span style={{ color: "var(--text3)", marginLeft: 8 }}>{r.labName}</span>
                </Td>
                <Td align="right">{r.openIssues}</Td>
                <Td align="right">
                  {r.escalatedIssues > 0 ? (
                    <span style={{ color: "var(--red)", fontWeight: 600 }}>
                      {r.escalatedIssues}
                    </span>
                  ) : (
                    0
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function RecentEscalationsPanel({ rows }: { rows: RecentEscalation[] }) {
  return (
    <div
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 12 }}>最近升級的 issue</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>暫無升級紀錄。</div>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {rows.map((r) => (
            <li
              key={r.id}
              style={{
                padding: "8px 0",
                borderBottom: "1px solid var(--border2)",
                fontSize: 13,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ color: "var(--text)" }}>{r.title}</span>
                <span style={{ color: "var(--text3)", fontSize: 11, whiteSpace: "nowrap" }}>
                  Lv {r.escalationLevel} · {new Date(r.updatedAt).toLocaleString("zh-TW")}
                </span>
              </div>
              <span
                style={{
                  display: "inline-block",
                  marginTop: 4,
                  fontSize: 11,
                  color: "var(--text3)",
                }}
              >
                severity {SeverityLabel[r.severity] ?? r.severity}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Th({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th
      style={{
        textAlign: align,
        padding: "6px 8px",
        fontSize: 11,
        color: "var(--text3)",
        fontWeight: 600,
      }}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "right" }) {
  return <td style={{ padding: "8px", color: "var(--text)", textAlign: align }}>{children}</td>;
}
