import type { CSSProperties } from "react";

// 共用表格樣式沿用全站 tokens（避免重複定義）。
export { th, td, tdMono, linkBtn } from "@/constants/styles";

export const pageHeaderStyle: CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  marginBottom: 24,
};

export const pageTitleStyle: CSSProperties = {
  fontSize: 22,
  fontWeight: 800,
  letterSpacing: -0.5,
};

export const pageSubtitleStyle: CSSProperties = {
  fontSize: 12,
  color: "var(--text3)",
  marginTop: 4,
  fontFamily: "monospace",
};

export const conditionRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "9px 0",
  borderBottom: "1px solid var(--border2)",
  fontSize: 13,
};

export function bannerStyle(ok: boolean): CSSProperties {
  return {
    marginBottom: 16,
    padding: "8px 14px",
    borderRadius: 8,
    fontSize: 12.5,
    background: ok ? "rgba(63,185,80,0.1)" : "rgba(255,68,68,0.1)",
    border: `1px solid ${ok ? "rgba(63,185,80,0.3)" : "rgba(255,68,68,0.3)"}`,
    color: ok ? "var(--green)" : "var(--red)",
  };
}
