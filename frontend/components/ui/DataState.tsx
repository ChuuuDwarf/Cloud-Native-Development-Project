import type { ReactNode } from "react";

// 統一處理 loading / error / empty 三種狀態（development_standards.md 7.1）
export default function DataState({
  loading,
  error,
  empty,
  emptyText = "目前沒有資料",
  children,
}: {
  loading: boolean;
  error?: string | null;
  empty?: boolean;
  emptyText?: string;
  children: ReactNode;
}) {
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 48, color: "var(--text3)" }}>
        <div style={{ fontSize: 28, marginBottom: 10 }}>⏳</div>
        <div style={{ fontSize: 13 }}>載入中…</div>
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ textAlign: "center", padding: 48, color: "var(--red)" }}>
        <div style={{ fontSize: 28, marginBottom: 10 }}>⚠️</div>
        <div style={{ fontSize: 13 }}>{error}</div>
      </div>
    );
  }
  if (empty) {
    return (
      <div style={{ textAlign: "center", padding: 48, color: "var(--text3)" }}>
        <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.5 }}>📭</div>
        <div style={{ fontSize: 14 }}>{emptyText}</div>
      </div>
    );
  }
  return <>{children}</>;
}

export function OfflineBanner() {
  return (
    <div
      style={{
        background: "rgba(247,129,102,0.1)",
        border: "1px solid rgba(247,129,102,0.25)",
        borderRadius: 10,
        padding: "8px 14px",
        marginBottom: 16,
        fontSize: 12,
        color: "var(--orange)",
      }}
    >
      ⚠️ 後端未連線，顯示離線展示資料；操作不會被儲存。請啟動 backend（uvicorn
      app.main:app）後重新整理。
    </div>
  );
}
