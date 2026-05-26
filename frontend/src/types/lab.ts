// Role D 模組共用型別（實驗執行 / 報告 / 結單 / 倉儲）
// 狀態值與後端 enums 一致，皆為中文字串。
// （由原 frontend/lib/types.ts 搬遷至 src/types/，對齊 README 結構。）

export type Role = "廠區使用者" | "實驗室人員" | "實驗室主管" | "系統管理者";

export const ROLES: Role[] = [
  "廠區使用者",
  "實驗室人員",
  "實驗室主管",
  "系統管理者",
];

// HTTP 標頭只能帶 ASCII，角色代碼對照（對應後端 deps.ROLE_CODES）
export const ROLE_CODE: Record<Role, string> = {
  廠區使用者: "user",
  實驗室人員: "staff",
  實驗室主管: "chief",
  系統管理者: "admin",
};

export interface HistoryEvent {
  time: string;
  action: string;
  by: string;
  note: string;
}

export interface AbortInfo {
  reason: string;
  by: string;
  status: "待主管判定" | "已終止" | "已駁回";
  requestedAt: string;
  resolution?: string;
}

export interface Wip {
  wipId: string;
  orderId: string;
  sample: string;
  experimentItem: string;
  machineId: string | null;
  recipe: string | null;
  status: string;
  progress: number;
  operator: string | null;
  checkInAt: string | null;
  checkOutAt: string | null;
  resultNote: string | null;
  rawDataUrl: string | null;
  experimentData?: Record<string, Record<string, string>>;
  dataVerified: boolean;
  abort: AbortInfo | null;
  history: HistoryEvent[];
}

export interface ReportVersion {
  version: number;
  status: string;
  at: string;
  by: string;
  note: string;
}

export interface Report {
  reportId: string;
  orderId: string;
  wipId: string;
  title: string;
  summary: string;
  conclusion: string;
  attachments: { name: string; at: string }[];
  status: string;
  experimentData?: Record<string, Record<string, string>>;
  createdAt: string;
  createdBy: string;
  versions: ReportVersion[];
}

export interface ReportTemplate {
  id: number;
  name: string;
  orderId: string | null;
  summary: string;
  conclusion: string;
  createdBy: string;
  createdAt: string;
}

export interface ClosureCondition {
  name: string;
  ok: boolean;
}

export interface ClosureCheck {
  orderId: string;
  status: string;
  canClose: boolean;
  conditions: ClosureCondition[];
}

export interface StorageItem {
  storageId: string;
  orderId: string;
  sample: string;
  qty: string;
  status: string;
  location: string;
  history: HistoryEvent[];
}

// 狀態 → Chip 樣式對應（Chip 元件支援的 type）
export type ChipType =
  | "draft"
  | "pending"
  | "review"
  | "approved"
  | "running"
  | "done"
  | "rejected"
  | "paused"
  | "idle";

const CHIP_MAP: Record<string, ChipType> = {
  // WIP / 委託單
  待派工: "pending",
  排程中: "review",
  待上機: "pending",
  執行中: "running",
  已下機: "paused",
  待確認: "review",
  待結果確認: "review",
  已完成: "done",
  實驗完成: "done",
  已終止: "rejected",
  實驗中: "running",
  暫停中: "paused",
  待主管判定: "paused",
  待報告回傳: "review",
  待取件: "approved",
  待送件: "approved",
  已結案: "done",
  排程: "review",
  // 報告
  草稿: "draft",
  待審核: "review",
  已確認: "approved",
  已發布: "done",
  已回傳: "done",
  已改版: "pending",
  // 倉儲
  實驗室: "idle",
  已入庫: "approved",
  待返還: "pending",
  已取件: "done",
};

export function chipOf(status: string): ChipType {
  return CHIP_MAP[status] ?? "idle";
}
