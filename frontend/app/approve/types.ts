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
  | "closed";

export type OrderAction = "approve" | "return" | "reject";

export type PriorityLevel = "normal" | "urgent" | "critical";

export type OrderItem = {
  id: number;
  sampleId: string;
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

export type ModalState =
  | { type: "none" }
  | { type: "message"; title: string; message: string }
  | { type: "detail"; title: string; order: Order }
  | { type: "history"; title: string; history: OrderHistory[] };

export type ReasonModalState =
  | { open: false }
  | {
      open: true;
      title: string;
      hint: string;
      action: OrderAction;
      order: Order;
      orderItem?: OrderItem;
      quotaOverride?: boolean;
      value: string;
    };
