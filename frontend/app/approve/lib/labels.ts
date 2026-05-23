import type { OrderAction, OrderStatus, PriorityLevel } from "../types";

export const statusLabel: Record<OrderStatus, string> = {
  draft: "草稿",
  pending_approval: "待簽核",
  cancelled: "已取消",
  approved: "已核准",
  returned: "退回補件",
  rejected: "已拒絕",
  sample_delivered: "已送樣",
  sample_received: "已收樣",
  ready_for_pickup: "待取件",
  closed: "已結案",
};

export const priorityLabel: Record<PriorityLevel, string> = {
  normal: "一般",
  urgent: "急件",
  critical: "特急件",
};

export const actionLabel: Record<OrderAction, string> = {
  approve: "核准",
  return: "退回補件",
  reject: "拒絕",
};
