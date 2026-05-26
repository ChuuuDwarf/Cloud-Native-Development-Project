import type { CSSProperties } from "react";

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

export const blockStyle: CSSProperties = {
  background: "var(--s2)",
  borderRadius: 8,
  padding: 12,
  marginBottom: 10,
  fontSize: 12.5,
};

export const blockLabelStyle: CSSProperties = {
  color: "var(--text3)",
  fontSize: 10,
  fontFamily: "monospace",
  marginBottom: 4,
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
