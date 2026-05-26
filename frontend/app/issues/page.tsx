"use client";

import { useQuery } from "@tanstack/react-query";
import { PermissionGuard } from "@/components/PermissionGuard";
import { issueApi } from "@/services/issue-api";
import { IssueStatusLabel, IssueTypeLabel, SeverityLabel } from "@/constants/status-labels";

export default function IssuePage() {
  return (
    <PermissionGuard requiredPermission="issues:read">
      <IssuePageContent />
    </PermissionGuard>
  );
}

function IssuePageContent() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["issues"],
    queryFn: () => issueApi.list(),
  });

  if (isLoading) {
    return <div style={{ padding: 24, color: "var(--text2)" }}>載入中...</div>;
  }

  if (isError) {
    return (
      <div style={{ padding: 24, color: "var(--red)" }}>載入失敗：{(error as Error).message}</div>
    );
  }

  const items = data?.items ?? [];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: "var(--text)", marginTop: 0, marginBottom: 16 }}>異常與警告</h1>

      {items.length === 0 ? (
        <div style={{ color: "var(--text2)" }}>目前沒有 issue。</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <Th>嚴重度</Th>
              <Th>標題</Th>
              <Th>類型</Th>
              <Th>狀態</Th>
              <Th>升級層級</Th>
              <Th>建立時間</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((issue) => (
              <tr key={issue.id} style={{ borderBottom: "1px solid var(--border2)" }}>
                <Td>
                  <SeverityChip severity={issue.severity} />
                </Td>
                <Td>{issue.title}</Td>
                <Td>{IssueTypeLabel[issue.type] ?? issue.type}</Td>
                <Td>{IssueStatusLabel[issue.status] ?? issue.status}</Td>
                <Td>{issue.escalationLevel}</Td>
                <Td>{new Date(issue.createdAt).toLocaleString("zh-TW")}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th
      style={{
        textAlign: "left",
        padding: "8px 12px",
        fontSize: 12,
        color: "var(--text3)",
        fontWeight: 600,
      }}
    >
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: "12px", fontSize: 13, color: "var(--text)" }}>{children}</td>;
}

function SeverityChip({ severity }: { severity: "low" | "medium" | "high" | "critical" }) {
  const colors = {
    low: "var(--text3)",
    medium: "var(--blue)",
    high: "#f59e0b",
    critical: "var(--red)",
  };
  return (
    <span
      style={{
        background: colors[severity],
        color: "#fff",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {SeverityLabel[severity] ?? severity}
    </span>
  );
}
