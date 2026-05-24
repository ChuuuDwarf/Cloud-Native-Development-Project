import type { CSSProperties } from "react";
import type { PriorityLevel } from "./types";

export const panelStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,.18)",
};

export const panelTitleStyle: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 16,
  fontWeight: 800,
};

export const inputStyle: CSSProperties = {
  width: "100%",
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: "9px 10px",
  outline: "none",
};

export const textareaStyle: CSSProperties = {
  width: "100%",
  minHeight: 120,
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: 10,
  resize: "vertical",
  outline: "none",
};

export const approvalCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  padding: 14,
};

export function priorityCardStyle(priority?: PriorityLevel): CSSProperties {
  if (priority === "critical") {
    return {
      border: "1px solid rgba(248, 81, 73, .8)",
      boxShadow: "0 0 0 1px rgba(248, 81, 73, .18), 0 10px 30px rgba(248, 81, 73, .12)",
    };
  }

  if (priority === "urgent") {
    return {
      border: "1px solid rgba(245, 158, 11, .8)",
      boxShadow: "0 0 0 1px rgba(245, 158, 11, .18), 0 10px 30px rgba(245, 158, 11, .10)",
    };
  }

  return {};
}

export const statusBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: 999,
  background: "rgba(56,139,253,.18)",
  color: "var(--blue)",
  fontSize: 11,
  fontWeight: 800,
  padding: "4px 8px",
  whiteSpace: "nowrap",
};

export function priorityBadgeStyle(priority: PriorityLevel): CSSProperties {
  const isCritical = priority === "critical";

  return {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 999,
    background: isCritical ? "rgba(248, 81, 73, .22)" : "rgba(245, 158, 11, .22)",
    border: isCritical ? "1px solid rgba(248, 81, 73, .55)" : "1px solid rgba(245, 158, 11, .55)",
    color: isCritical ? "#ffb4ad" : "#ffd28a",
    fontSize: 11,
    fontWeight: 900,
    padding: "4px 8px",
    whiteSpace: "nowrap",
  };
}

export const logStyle: CSSProperties = {
  background: "#05070a",
  border: "1px solid var(--border2)",
  borderRadius: 8,
  padding: 10,
  minHeight: 160,
  maxHeight: 260,
  overflow: "auto",
  color: "#a6e3a1",
  fontSize: 11,
  whiteSpace: "pre-wrap",
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

export const quotaExceededStyle: CSSProperties = {
  marginTop: 8,
  padding: 8,
  borderRadius: 8,
  background: "rgba(245, 158, 11, .12)",
  border: "1px solid rgba(245, 158, 11, .35)",
  color: "#ffd28a",
  fontSize: 12,
};

export const quotaNormalStyle: CSSProperties = {
  marginTop: 8,
  padding: 8,
  borderRadius: 8,
  background: "rgba(63, 185, 80, .08)",
  border: "1px solid rgba(63, 185, 80, .24)",
  color: "var(--green)",
  fontSize: 12,
};

export const quotaOverrideOkStyle: CSSProperties = {
  ...quotaExceededStyle,
  background: "rgba(63, 185, 80, .12)",
  border: "1px solid rgba(63, 185, 80, .35)",
  color: "var(--green)",
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

export const itemCardStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderLeft: "4px solid var(--blue)",
  borderRadius: 10,
  padding: 12,
};

export const timelineItemStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 12,
  marginBottom: 12,
};

export const cardTitleStyle: CSSProperties = {
  margin: "0 0 10px",
  fontSize: 15,
  fontWeight: 800,
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
    fontSize: 12,
  };
}

export const itemApprovalStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 10,
};

export const approvableItemStyle: CSSProperties = {
  ...itemApprovalStyle,
  border: "1px solid rgba(63, 185, 80, .65)",
  boxShadow: "0 0 0 1px rgba(63, 185, 80, .12)",
};
