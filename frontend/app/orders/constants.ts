import type {
  MasterData,
  OrderAction,
  OrderStatus,
  OrderStatusFilter,
  PriorityLevel,
} from "./types";

export const templateStoragePrefix = "order-management-templates";

export const emptyFormItem = {
  sampleId: "",
  sampleName: "",
  labId: "",
  experimentId: "",
  targetGroup: "G1",
  target: 1,
  check: false,
};

export const emptyMasterData: MasterData = {
  departments: [],
  labs: [],
  experiments: [],
};

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
  // 跨模組下游狀態（C 排程 / D 執行・結案寫入），A 僅顯示。
  waiting_sample: "待送樣",
  received: "已收樣",
  split: "已分貨",
  scheduled: "排程中",
  in_progress: "實驗中",
  waiting_result_confirm: "待結果確認",
  completed: "實驗完成",
  waiting_report_return: "待報告回傳",
  waiting_pickup: "待送件",
};

export const priorityLabel: Record<PriorityLevel, string> = {
  normal: "一般",
  urgent: "急件",
  critical: "特急件",
  low: "低",
  medium: "中",
  high: "高",
};

export const actionLabel: Record<OrderAction, string> = {
  submit: "送出簽核",
  cancel: "取消委託單",
  confirm_delivery: "確認送樣",
  confirm_received: "確認收樣",
  ready_for_pickup: "待取件",
  close: "結案",
};

export const allowedActions: Record<OrderStatus, OrderAction[]> = {
  draft: ["submit", "cancel"],
  returned: ["submit", "cancel"],
  pending_approval: ["cancel"],
  approved: ["confirm_delivery"],
  sample_delivered: [],
  sample_received: ["ready_for_pickup"],
  ready_for_pickup: ["close"],
  closed: [],
  rejected: [],
  cancelled: [],
  // 跨模組下游狀態：A 不在這些階段提供操作。
  waiting_sample: [],
  received: [],
  split: [],
  scheduled: [],
  in_progress: [],
  waiting_result_confirm: [],
  completed: [],
  waiting_report_return: [],
  waiting_pickup: [],
};

export const orderStatusFilters: { value: OrderStatusFilter; label: string }[] = [
  { value: "all", label: "所有委託單" },
  { value: "draft", label: "草稿" },
  { value: "pending_approval", label: "待簽核" },
  { value: "returned", label: "退回補件" },
  { value: "rejected", label: "已拒絕" },
  { value: "approved", label: "已核准" },
  { value: "sample_delivered", label: "已送樣" },
  { value: "sample_received", label: "已收樣" },
  { value: "ready_for_pickup", label: "待取件" },
  { value: "closed", label: "已結案" },
  { value: "cancelled", label: "已取消" },
];
