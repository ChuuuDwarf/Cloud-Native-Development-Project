import type { Order, OrderItem } from "../types";

export function formatDate(value?: string | null) {
  if (!value) return "-";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getEffectiveItemStatus(order: Order, item: OrderItem) {
  if (order.status === "pending_approval" && (!item.status || item.status === "draft")) {
    return "pending_approval";
  }

  return item.status || "-";
}

export function quotaStatusText(item: OrderItem) {
  if (item.quotaOverride) return "配額：已特批";
  if (item.quotaExceeded) return "配額：需特批";
  return "配額：正常";
}
