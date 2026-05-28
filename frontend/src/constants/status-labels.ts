// Hand-written Chinese display labels for every shared enum.
// Keep the keys in lockstep with `./enums.ts` (which is auto-generated).
// If you add a new enum value upstream, the type-checker will flag the missing
// entry here.

import type {
  IssueAction,
  IssueStatus,
  IssueType,
  MachineStatus,
  NotificationChannel,
  NotificationStatus,
  OrderAction,
  OrderStatus,
  ReportAction,
  ReportStatus,
  Severity,
  UserStatus,
  WipAction,
  WipStatus,
} from "./enums";

export const OrderStatusLabel: Record<OrderStatus, string> = {
  draft: "草稿",
  pending_approval: "待簽核",
  returned: "退回補件",
  rejected: "已拒絕",
  approved: "已核准",
  waiting_sample: "待送樣",
  received: "已收樣",
  split: "已分貨",
  scheduled: "排程中",
  in_progress: "實驗中",
  waiting_result_confirm: "待結果確認",
  completed: "實驗完成",
  waiting_report_return: "待報告回傳",
  waiting_pickup: "待送件",
  closed: "已結案",
  cancelled: "已取消",
};

export const OrderActionLabel: Record<OrderAction, string> = {
  submit: "送出簽核",
  cancel: "取消",
  approve: "核准",
  return: "退回",
  reject: "拒絕",
  confirm_delivery: "確認送樣",
  confirm_received: "確認收樣",
  ready_for_pickup: "通知取件",
  close: "結案",
};

export const WipStatusLabel: Record<WipStatus, string> = {
  created: "已建立",
  waiting_dispatch: "待派工",
  in_schedule: "排程中",
  waiting_load: "待上機",
  running: "執行中",
  unloaded: "已下機",
  waiting_confirm: "待確認",
  completed: "已完成",
  terminated: "已終止",
};

export const WipActionLabel: Record<WipAction, string> = {
  dispatch: "派工",
  schedule: "排程",
  load: "上機",
  unload: "下機",
  confirm: "確認",
  terminate: "終止",
  reopen: "重開",
};

export const MachineStatusLabel: Record<MachineStatus, string> = {
  idle: "閒置",
  in_use: "使用中",
  maintenance: "保養中",
  faulty: "故障中",
  disabled: "停用",
};

export const ReportStatusLabel: Record<ReportStatus, string> = {
  draft: "草稿",
  pending_review: "待審核",
  confirmed: "已確認",
  published: "已發布",
  returned: "已退回",
  revised: "已修訂",
};

export const ReportActionLabel: Record<ReportAction, string> = {
  submit_review: "送審",
  approve: "核准",
  reject: "拒絕",
  publish: "發布",
  return_to_user: "退回給使用者",
  create_revision: "建立修訂版",
};

export const IssueStatusLabel: Record<IssueStatus, string> = {
  open: "未處理",
  assigned: "已指派",
  escalated: "已升級",
  acknowledged: "已處理",
  closed: "已關閉",
};

export const IssueActionLabel: Record<IssueAction, string> = {
  approve: "核准",
  reject: "拒絕",
  close: "關閉",
  escalate: "升級",
  assign: "指派",
  reopen: "重啟",
};

export const IssueTypeLabel: Record<IssueType, string> = {
  abnormal: "異常",
  warning: "告警",
  termination_request: "中止申請",
};

export const NotificationStatusLabel: Record<NotificationStatus, string> = {
  unread: "未讀",
  read: "已讀",
};

export const NotificationChannelLabel: Record<NotificationChannel, string> = {
  in_app: "站內通知",
  email: "Email",
  phone: "電話通知",
};

export const UserStatusLabel: Record<UserStatus, string> = {
  active: "啟用",
  disabled: "停用",
};

export const SeverityLabel: Record<Severity, string> = {
  low: "低",
  medium: "中",
  high: "高",
  critical: "嚴重",
};
