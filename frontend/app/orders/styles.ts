import type { CSSProperties } from "react";

export const pageHeaderStyle: CSSProperties = {
  marginBottom: 24,
  display: "flex",
  justifyContent: "space-between",
  gap: 16,
  alignItems: "flex-start",
};

export const pageTitleStyle: CSSProperties = { fontSize: 22, fontWeight: 800, margin: 0 };

export const pageSubtitleStyle: CSSProperties = {
  color: "var(--text3)",
  fontSize: 12,
  marginTop: 4,
  fontFamily: "monospace",
};

export const workspaceStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "340px 1fr",
  gap: 16,
};

export const orderWorkspaceGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "320px minmax(0, 1fr)",
  alignItems: "start",
  gap: 16,
};

export const quotaSummaryStyle: CSSProperties = {
  position: "relative",
  background: "linear-gradient(135deg, rgba(56,139,253,.16), var(--s1))",
  border: "1px solid rgba(56,139,253,.35)",
  borderRadius: 12,
  padding: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,.18)",
};

export const summaryTitleStyle: CSSProperties = { margin: 0, fontSize: 16, fontWeight: 800 };
export const summaryTextStyle: CSSProperties = { color: "var(--text3)", fontSize: 12, margin: "6px 0 0" };

export const quotaSummaryItemStyle: CSSProperties = {
  background: "rgba(13, 17, 23, .46)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 10,
};

export const quotaDetailListStyle: CSSProperties = { display: "grid", gap: 10, marginTop: 14 };
export const filterTabsStyle: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 };

export function filterTabStyle(active: boolean): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    background: active ? "var(--blue)" : "var(--s2)",
    border: active ? "1px solid var(--blue)" : "1px solid var(--border2)",
    borderRadius: 999,
    color: active ? "#fff" : "var(--text2)",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 800,
    padding: "7px 10px",
  };
}

export const filterCountStyle: CSSProperties = {
  background: "rgba(255,255,255,.14)",
  borderRadius: 999,
  padding: "1px 6px",
};

export const panelStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,.18)",
};

export const panelTitleStyle: CSSProperties = { margin: "0 0 12px", fontSize: 16, fontWeight: 800 };

export const inputStyle: CSSProperties = {
  width: "100%",
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: "9px 10px",
  outline: "none",
};

export const sectionHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginTop: 16,
};

export const orderCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  padding: 14,
};

export const itemCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 12,
};

export const experimentChecklistStyle: CSSProperties = { display: "grid", gap: 10, marginTop: 12 };
export const experimentLabGroupStyle: CSSProperties = { border: "1px solid var(--border)", borderRadius: 8, padding: 10 };
export const checkboxRowStyle: CSSProperties = { display: "flex", alignItems: "center", gap: 8, color: "var(--text2)", fontSize: 12 };
export const subItemStyle: CSSProperties = { borderTop: "1px solid var(--border)", paddingTop: 10 };
export const experimentHeaderStyle: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" };

export const editNoticeStyle: CSSProperties = {
  padding: 10,
  borderRadius: 8,
  background: "rgba(245, 158, 11, .12)",
  border: "1px solid rgba(245, 158, 11, .35)",
  color: "var(--text2)",
  fontSize: 12,
  marginBottom: 12,
};

export const templateBoxStyle: CSSProperties = {
  background: "rgba(56,139,253,.08)",
  border: "1px solid rgba(56,139,253,.28)",
  borderRadius: 10,
  padding: 12,
  marginTop: 12,
};

export const statusBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: 999,
  background: "rgba(56,139,253,.18)",
  color: "var(--blue)",
  fontSize: 11,
  fontWeight: 800,
  padding: "4px 8px",
  height: 24,
  whiteSpace: "nowrap",
};

export const emptyStyle: CSSProperties = {
  padding: 18,
  textAlign: "center",
  color: "var(--text3)",
  border: "1px dashed var(--border)",
  borderRadius: 10,
  background: "var(--s2)",
};

export const reasonBoxStyle: CSSProperties = {
  marginTop: 10,
  padding: 10,
  borderRadius: 8,
  background: "rgba(245, 158, 11, .12)",
  border: "1px solid rgba(245, 158, 11, .35)",
  color: "var(--text2)",
  fontSize: 12,
};

export const orderItemStatusStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 10,
};

export const quotaBoxStyle: CSSProperties = {
  marginTop: 12,
  padding: 10,
  borderRadius: 8,
  background: "rgba(56,139,253,.12)",
  border: "1px solid rgba(56,139,253,.35)",
  color: "var(--text)",
};

export const modalOverlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,.58)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
  zIndex: 50,
};

export const modalStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 14,
  width: "min(900px, 94vw)",
  maxHeight: "86vh",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

export const modalHeaderStyle: CSSProperties = {
  padding: "14px 18px",
  borderBottom: "1px solid var(--border2)",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
};

export const infoCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  padding: 14,
  marginBottom: 12,
};

export const timelineItemStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 12,
  marginBottom: 12,
};

export const cardTitleStyle: CSSProperties = { margin: "0 0 10px", fontSize: 15, fontWeight: 800 };

export const selectedTemplateSummaryStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  marginTop: 10,
  padding: 12,
};

export const logStyle: CSSProperties = {
  background: "#05070a",
  border: "1px solid var(--border2)",
  borderRadius: 8,
  padding: 10,
  minHeight: 120,
  maxHeight: 220,
  overflow: "auto",
  color: "#a6e3a1",
  fontSize: 11,
  whiteSpace: "pre-wrap",
};

export const footerActionsStyle: CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  flexWrap: "wrap",
  gap: 8,
  marginTop: 16,
  position: "relative",
  zIndex: 30,
  pointerEvents: "auto",
};

export function buttonStyle(kind: "blue" | "green" | "gray" | "red"): CSSProperties {
  const colors = {
    blue: "var(--blue)",
    green: "var(--green)",
    gray: "var(--s3)",
    red: "var(--red)",
  };

  return {
    background: colors[kind],
    color: kind === "gray" ? "var(--text2)" : "#fff",
    border: "1px solid var(--border)",
    borderRadius: 7,
    padding: "7px 10px",
    cursor: "pointer",
    pointerEvents: "auto",
    fontSize: 12,
  };
}
