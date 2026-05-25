export type WipStatus = "待派工" | "排程中" | "待上機";

export type Strategy =
  | "FIFO"
  | "Priority First"
  | "Earliest Due Date"
  | "Least Setup Change"
  | "Hybrid";

export interface Dispatch {
  dispatchId: string;
  wipId: string;
  orderId: string;
  experimentItem: string;
  priority: string;
  lab: string;
  dueAt: string;
  status: WipStatus;
  suggestedMachineId?: string | null;
  assignedMachineId?: string | null;
  assignedRecipeId?: string | null;
  scheduledStart?: string | null;
  scheduledEnd?: string | null;
  createdBy?: string | null;
  assignedBy?: string | null;
  strategy?: string | null;
  replanReason?: string | null;
}

export interface CreateDispatchPayload {
  dispatchId: string;
  wipId: string;
  orderId: string;
  experimentItem: string;
  priority: string;
  dueAt: string;
}

export interface AssignDispatchPayload {
  machineId: string;
  recipeId: string;
  scheduledStart: string;
  scheduledEnd: string;
}
