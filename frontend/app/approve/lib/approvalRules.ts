import type { Order, OrderItem, PriorityLevel } from "../types";

const priorityRank: Record<PriorityLevel, number> = {
  critical: 0,
  urgent: 1,
  normal: 2,
};

export function sortApprovalOrders(items: Order[]) {
  return [...items].sort((a, b) => {
    const priorityDiff =
      priorityRank[a.priority || "normal"] - priorityRank[b.priority || "normal"];
    if (priorityDiff !== 0) return priorityDiff;
    return new Date(b.applyDate).getTime() - new Date(a.applyDate).getTime();
  });
}

export function isHighPriority(priority?: PriorityLevel) {
  return priority === "critical" || priority === "urgent";
}

export function getEffectiveItemStatus(order: Order, item: OrderItem) {
  if (order.status === "pending_approval" && (!item.status || item.status === "draft")) {
    return "pending_approval";
  }

  return item.status || "-";
}

export function canActorApproveItem(actorLabIds: string[], order: Order, item: OrderItem) {
  return (
    order.status === "pending_approval" &&
    actorLabIds.includes(item.labId) &&
    getEffectiveItemStatus(order, item) === "pending_approval"
  );
}

export function orderHasQuotaExceededReason(order: Order) {
  return Boolean(order.lastReason?.includes("配額") || order.lastReason?.includes("超額"));
}

export function itemNeedsQuotaOverride(order: Order, item: OrderItem) {
  return !item.quotaOverride && (item.quotaExceeded ?? orderHasQuotaExceededReason(order));
}

export function quotaStatusText(order: Order, item: OrderItem) {
  if (item.quotaOverride) return "配額：已特批";
  if (itemNeedsQuotaOverride(order, item)) return "配額：需特批";
  return "配額：正常";
}

export function approvableItemsForActor(actorLabIds: string[], order: Order) {
  return (order.items || []).filter((item) => canActorApproveItem(actorLabIds, order, item));
}
