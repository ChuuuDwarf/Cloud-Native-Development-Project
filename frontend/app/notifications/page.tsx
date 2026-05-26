"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PermissionGuard } from "@/components/PermissionGuard";
import { NotificationStatus, type Severity } from "@/constants/enums";
import {
  NotificationChannelLabel,
  NotificationStatusLabel,
  SeverityLabel,
} from "@/constants/status-labels";
import { notificationApi } from "@/services/notification-api";
import type { NotificationResponse } from "@/types/notification";

export default function NotificationsPage() {
  return (
    <PermissionGuard requiredPermission="notifications:read">
      <NotificationsPageContent />
    </PermissionGuard>
  );
}

function NotificationsPageContent() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationApi.list(),
    // Soft polling so a freshly created issue / escalation shows up
    // without a manual refresh. SSE push (per Phase 4 plan) replaces
    // this later; until then 15s is the eng-team tolerable cadence.
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });

  const markRead = useMutation({
    mutationFn: (ids: string[]) => notificationApi.markRead({ ids }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => {
      console.error("markRead failed:", err);
      alert("標記為已讀失敗，請稍後再試。");
    },
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
  const unreadIds = items.filter((n) => n.status === NotificationStatus.Unread).map((n) => n.id);

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <h1 style={{ color: "var(--text)", margin: 0 }}>通知中心</h1>
        <button
          onClick={() => markRead.mutate(unreadIds)}
          disabled={unreadIds.length === 0 || markRead.isPending}
          style={{
            background: unreadIds.length === 0 ? "var(--s2)" : "var(--blue)",
            color: "#fff",
            border: "none",
            padding: "6px 14px",
            borderRadius: 6,
            cursor: unreadIds.length === 0 ? "not-allowed" : "pointer",
            fontSize: 13,
            opacity: markRead.isPending ? 0.6 : 1,
          }}
        >
          {markRead.isPending ? "處理中..." : `全部標為已讀 (${unreadIds.length})`}
        </button>
      </div>

      {items.length === 0 ? (
        <div style={{ color: "var(--text2)" }}>目前沒有通知。</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <Th>嚴重度</Th>
              <Th>標題</Th>
              <Th>內容</Th>
              <Th>管道</Th>
              <Th>狀態</Th>
              <Th>建立時間</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((n) => (
              <NotificationRow
                key={n.id}
                notification={n}
                onMarkRead={() => markRead.mutate([n.id])}
                disabled={markRead.isPending}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function NotificationRow({
  notification: n,
  onMarkRead,
  disabled,
}: {
  notification: NotificationResponse;
  onMarkRead: () => void;
  disabled: boolean;
}) {
  const isUnread = n.status === NotificationStatus.Unread;
  return (
    <tr
      style={{
        borderBottom: "1px solid var(--border2)",
        background: isUnread ? "rgba(56,139,253,0.05)" : "transparent",
        cursor: isUnread ? "pointer" : "default",
      }}
      onClick={isUnread && !disabled ? onMarkRead : undefined}
      title={isUnread ? "點擊標為已讀" : ""}
    >
      <Td>
        <SeverityChip severity={n.severity} />
      </Td>
      <Td>
        <span style={{ fontWeight: isUnread ? 600 : 400 }}>{n.title}</span>
      </Td>
      <Td>
        <span style={{ color: "var(--text2)" }}>{n.body || "—"}</span>
      </Td>
      <Td>
        {CHANNEL_ICON[n.channel] ?? "📨"} {NotificationChannelLabel[n.channel] ?? n.channel}
      </Td>
      <Td>{NotificationStatusLabel[n.status] ?? n.status}</Td>
      <Td>{new Date(n.createdAt).toLocaleString("zh-TW")}</Td>
    </tr>
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

const CHANNEL_ICON: Record<string, string> = {
  in_app: "🔔",
  email: "✉️",
  phone: "📞",
};
