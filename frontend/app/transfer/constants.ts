import type { CurrentUser } from "./types";

export const fallbackUser: CurrentUser = {
  id: "fallback",
  name: "張志明",
  role: "lab_engineer",
  role_name: "實驗室人員",
  department: "Lab A",
  lab_name: "Lab A",
  email: "",
};

export const sampleStatusText: Record<string, string> = {
  pending_receive: "待收樣",
  received: "已收樣",
  split: "已分貨",
  pending_transfer: "可交接",
  transferring: "交接中",
  in_storage: "已入庫",
  outbound: "待取件",
  picked_up: "已取件",
  lost: "遺失",
  damaged: "破損",
  cancelled: "已取消",
};

export const transferStatusText: Record<string, string> = {
  pending: "交接申請已建立",
  transferring: "已送出 / 待對方收樣",
  received: "已簽收",
  cancelled: "已取消",
};

export const wipStatusText: Record<string, string> = {
  created: "已建立",
  waiting_schedule: "待排程",
  scheduled: "已排程",
  dispatched: "已派工",
  running: "執行中",
  paused: "暫停",
  completed: "已完成",
  terminated: "已終止",
  cancelled: "已取消",
};

export const priorityText: Record<string, string> = {
  low: "低",
  normal: "一般",
  high: "高",
  urgent: "急件",
};

export const blockingTransferStatuses = ["pending", "transferring"];
