/**
 * Shared inline style constants.
 *
 * All pages should import from here instead of defining their own
 * inputStyle / primaryBtn / etc.
 */

import type { CSSProperties } from "react";

export const inputStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  fontSize: 13,
  padding: "9px 12px",
  outline: "none",
  width: "100%",
};

export const primaryBtn: CSSProperties = {
  padding: "8px 14px",
  background: "linear-gradient(135deg,#388bfd,#39d0d8)",
  color: "#fff",
  fontWeight: 700,
  border: "none",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: 12,
};

export const secondaryBtn: CSSProperties = {
  padding: "6px 10px",
  background: "transparent",
  color: "var(--text2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 11,
};

export const selectStyle: CSSProperties = {
  ...inputStyle,
  appearance: "none",
  cursor: "pointer",
};

export const th: CSSProperties = {
  fontSize: 10,
  letterSpacing: 1.5,
  color: "var(--text3)",
  padding: "10px 16px",
  textAlign: "left",
  fontFamily: "monospace",
  borderBottom: "1px solid var(--border2)",
  whiteSpace: "nowrap",
};

export const td: CSSProperties = {
  padding: "11px 16px",
  fontSize: 12.5,
  verticalAlign: "middle",
};

export const tdMono: CSSProperties = {
  ...td,
  fontFamily: "monospace",
  fontSize: 11.5,
  color: "var(--text2)",
};

export const linkBtn: CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--blue)",
  cursor: "pointer",
  fontFamily: "monospace",
  fontSize: 11.5,
  padding: 0,
  textDecoration: "underline",
};

export const roleBadge: CSSProperties = {
  display: "inline-block",
  background: "rgba(56,139,253,0.15)",
  color: "var(--blue)",
  border: "1px solid rgba(56,139,253,0.4)",
  padding: "1px 8px",
  borderRadius: 8,
  fontSize: 10,
  marginRight: 4,
  fontFamily: "monospace",
};
