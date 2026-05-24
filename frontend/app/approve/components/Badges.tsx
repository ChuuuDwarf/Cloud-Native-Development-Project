import type { OrderStatus, PriorityLevel } from "../types";
import { statusLabel } from "../lib/labels";
import { priorityBadgeStyle, statusBadgeStyle } from "../styles";

export function StatusBadge({ status }: { status: OrderStatus }) {
  return <span style={statusBadgeStyle}>{statusLabel[status] || status}</span>;
}

export function PriorityBadge({ priority }: { priority: PriorityLevel }) {
  if (priority === "normal") return null;

  return (
    <span style={priorityBadgeStyle(priority)}>{priority === "critical" ? "特急件" : "急件"}</span>
  );
}
