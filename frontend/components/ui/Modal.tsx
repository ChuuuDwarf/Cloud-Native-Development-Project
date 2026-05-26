"use client";
import type { ReactNode } from "react";

export default function Modal({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(6px)",
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--s1)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          width: 560,
          maxHeight: "85vh",
          overflowY: "auto",
          boxShadow: "0 0 80px rgba(56,139,253,0.15)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: "18px 22px",
            borderBottom: "1px solid var(--border2)",
            gap: 10,
            position: "sticky",
            top: 0,
            background: "var(--s1)",
          }}
        >
          <span style={{ fontSize: 15, fontWeight: 700, flex: 1 }}>{title}</span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "var(--text3)",
              fontSize: 22,
              cursor: "pointer",
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: 22 }}>{children}</div>
        {footer && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 10,
              padding: "14px 22px",
              borderTop: "1px solid var(--border2)",
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

// 表單欄位
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 5,
        marginBottom: 14,
      }}
    >
      <label
        style={{
          fontSize: 10,
          color: "var(--text3)",
          fontFamily: "monospace",
          letterSpacing: 1,
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

export const inputStyle = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "9px 12px",
  borderRadius: 8,
  fontSize: 13,
  outline: "none",
  fontFamily: "inherit",
  width: "100%",
} as const;
