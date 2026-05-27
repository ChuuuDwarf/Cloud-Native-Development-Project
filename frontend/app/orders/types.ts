export type OrderStatus =
  | "draft"
  | "pending_approval"
  | "cancelled"
  | "approved"
  | "returned"
  | "rejected"
  | "sample_delivered"
  | "sample_received"
  | "ready_for_pickup"
  | "closed"
  // Cross-module downstream statuses written into the shared orders table by
  // C (排程) and D (執行/結案). A doesn't act on these but must display them.
  | "waiting_sample"
  | "received"
  | "split"
  | "scheduled"
  | "in_progress"
  | "waiting_result_confirm"
  | "completed"
  | "waiting_report_return"
  | "waiting_pickup";

export type OrderAction =
  | "submit"
  | "cancel"
  | "confirm_delivery"
  | "confirm_received"
  | "ready_for_pickup"
  | "close";

export type PriorityLevel = "normal" | "urgent" | "critical" | "low" | "medium" | "high";
export type OrderStatusFilter = "all" | OrderStatus;

export type Department = { id: string; code?: string; name: string };
export type Lab = { id: string; code?: string; name: string; capacity?: number };
export type Experiment = { id: string; name: string; labId: string };

export type MasterData = {
  departments: Department[];
  labs: Lab[];
  experiments: Experiment[];
  statuses?: { value: string; label: string }[];
};

export type UserNameLookup = Record<string, string | undefined>;

export type TemplateMasterData = Pick<MasterData, "labs" | "experiments">;

export type FormItem = {
  sampleId: string;
  sampleName: string;
  labId: string;
  experimentId: string;
};

export type OrderTemplate = {
  id: string;
  name: string;
  items: FormItem[];
  createdAt: string;
  updatedAt?: string;
};

export type OrderItem = {
  id: number;
  sampleId: string;
  sampleName?: string | null;
  labId: string;
  experimentId: string;
  status?: OrderStatus;
  approvedBy?: string | null;
  approvedAt?: string | null;
  returnReason?: string | null;
  rejectReason?: string | null;
  quotaExceeded?: boolean;
  quotaOverride?: boolean;
};

export type Order = {
  id: number;
  orderNo: string;
  applicantId: string;
  departmentId: string;
  applyDate: string;
  status: OrderStatus;
  priority?: PriorityLevel;
  totalItems: number;
  lastReason?: string | null;
  createdAt: string;
  updatedAt: string;
  items?: OrderItem[];
};

export type OrderHistory = {
  id: number;
  orderId: number;
  actorId: string;
  action: string;
  fromStatus?: string | null;
  toStatus: string;
  reason?: string | null;
  quotaOverride: boolean;
  actionTime: string;
};

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  message?: string;
};

export type QuotaCheckItem = {
  scopeType: string;
  scopeId: string;
  used: number;
  limit: number;
  requested: number;
  allowed: boolean;
  needOverride: boolean;
};

export type QuotaCheck = {
  allowed: boolean;
  needOverride: boolean;
  checks: QuotaCheckItem[];
};

export type QuotaSetting = {
  id: number;
  scopeType: string;
  scopeId: string;
  monthlyLimit: number;
  isActive: boolean;
  usedCount?: number;
  remaining?: number;
  reservedCount?: number;
  effectiveUsedCount?: number;
};

export type ModalState =
  | { type: "none" }
  | { type: "message"; title: string; message: string }
  | { type: "detail"; title: string; order: Order }
  | { type: "history"; title: string; history: OrderHistory[] };

export type SampleFormGroup = {
  sampleId: string;
  sampleName: string;
  startIndex: number;
  endIndex: number;
  items: { item: FormItem; index: number }[];
};
