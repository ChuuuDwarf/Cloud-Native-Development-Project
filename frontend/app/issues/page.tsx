"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PermissionGuard } from "@/components/PermissionGuard";
import { type Severity } from "@/constants/enums";
import {
  IssueStatusLabel,
  IssueTypeLabel,
  RoleLabel,
  SeverityLabel,
  type RoleName,
} from "@/constants/status-labels";
import { issueApi } from "@/services/issue-api";
import type { IssueAcknowledgement, IssueResponse } from "@/types/issue";

export default function IssuePage() {
  return (
    <PermissionGuard requiredPermission="issues:read">
      <IssuePageContent />
    </PermissionGuard>
  );
}

function IssuePageContent() {
  const [activeIssue, setActiveIssue] = useState<IssueResponse | null>(null);

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
              <Th>動作</Th>
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
                <Td>
                  <button
                    onClick={() => setActiveIssue(issue)}
                    style={{
                      background: "transparent",
                      border: "1px solid var(--blue)",
                      color: "var(--blue)",
                      padding: "4px 10px",
                      borderRadius: 4,
                      fontSize: 12,
                      cursor: "pointer",
                    }}
                  >
                    詳細
                  </button>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {activeIssue && <IssueDetailModal issue={activeIssue} onClose={() => setActiveIssue(null)} />}
    </div>
  );
}

function IssueDetailModal({ issue, onClose }: { issue: IssueResponse; onClose: () => void }) {
  const {
    data: acks,
    isLoading: acksLoading,
    isError: acksIsError,
    error: acksError,
  } = useQuery({
    queryKey: ["issue", issue.id, "acknowledgements"],
    queryFn: () => issueApi.listAcknowledgements(issue.id),
  });

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--s1)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: 24,
          width: "min(640px, 92vw)",
          maxHeight: "85vh",
          overflowY: "auto",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <h2 style={{ color: "var(--text)", margin: 0, fontSize: 18 }}>{issue.title}</h2>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text2)",
              fontSize: 20,
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 8, fontSize: 13 }}>
          <Label>嚴重度</Label>
          <Value>
            <SeverityChip severity={issue.severity} />
          </Value>

          <Label>類型</Label>
          <Value>{IssueTypeLabel[issue.type] ?? issue.type}</Value>

          <Label>狀態</Label>
          <Value>{IssueStatusLabel[issue.status] ?? issue.status}</Value>

          <Label>升級層級</Label>
          <Value>Lv {issue.escalationLevel}</Value>

          <Label>對象類型</Label>
          <Value>{issue.targetType}</Value>

          <Label>對象 ID</Label>
          <Value style={{ fontFamily: "monospace" }}>{issue.targetId}</Value>

          <Label>所屬實驗室</Label>
          <Value
            style={
              issue.labCode
                ? undefined
                : { fontFamily: "monospace", fontSize: 11 }
            }
          >
            {issue.labCode ?? issue.labId}
          </Value>

          <Label>建立時間</Label>
          <Value>{new Date(issue.createdAt).toLocaleString("zh-TW")}</Value>

          {issue.description && (
            <>
              <Label>說明</Label>
              <Value>{issue.description}</Value>
            </>
          )}
        </div>

        <h3 style={{ color: "var(--text)", marginTop: 24, marginBottom: 8, fontSize: 14 }}>
          已確認 ({acks?.length ?? 0})
        </h3>
        {acksLoading ? (
          <div style={{ color: "var(--text2)", fontSize: 12 }}>載入中...</div>
        ) : acksIsError ? (
          <div style={{ color: "var(--red)", fontSize: 12 }}>
            載入確認紀錄失敗：{(acksError as Error)?.message ?? "未知錯誤"}
          </div>
        ) : acks && acks.length > 0 ? (
          <AcknowledgementList items={acks} />
        ) : (
          <div style={{ color: "var(--text2)", fontSize: 12 }}>尚無人確認此通知。</div>
        )}
      </div>
    </div>
  );
}

function AcknowledgementList({ items }: { items: IssueAcknowledgement[] }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--border)" }}>
          <Th>姓名</Th>
          <Th>角色</Th>
          <Th>管道</Th>
          <Th>確認時間</Th>
        </tr>
      </thead>
      <tbody>
        {items.map((a) => (
          <tr
            key={`${a.userId}-${a.channel}-${a.readAt}`}
            style={{ borderBottom: "1px solid var(--border2)" }}
          >
            <Td>
              {a.userName}
              <span style={{ color: "var(--text3)", fontSize: 10, marginLeft: 6 }}>
                {a.userEmail}
              </span>
            </Td>
            <Td>{a.role ? (RoleLabel[a.role as RoleName] ?? a.role) : "—"}</Td>
            <Td>{a.channel}</Td>
            <Td>{new Date(a.readAt).toLocaleString("zh-TW")}</Td>
          </tr>
        ))}
      </tbody>
    </table>
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

function Label({ children }: { children: React.ReactNode }) {
  return <div style={{ color: "var(--text3)", padding: "4px 0" }}>{children}</div>;
}

function Value({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ color: "var(--text)", padding: "4px 0", ...style }}>{children}</div>;
}

function SeverityChip({ severity }: { severity: Severity }) {
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
