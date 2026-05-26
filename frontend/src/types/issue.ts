import type { IssueStatus, IssueType, Severity } from "@/constants/enums";

// === API response shape (matches backend IssueRead) ===
export interface IssueResponse {
  id: string;
  type: IssueType;
  targetType: string;
  targetId: string;
  labId: string;
  title: string;
  description: string;
  severity: Severity;
  status: IssueStatus;
  assignedTo: string | null;
  escalationLevel: number | null;
  nextEscalationTime: string | null;
  handledAt: string | null;
  closedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

// === Request payloads (matches backend IssueCreate / IssueUpdate) ===
export interface CreateIssuePayload {
  type: IssueType;
  targetType: string;
  targetId: string;
  labId: string;
  title: string;
  description?: string;
  severity?: Severity;
  assignedTo?: string | null;
}

export interface UpdateIssuePayload {
  title?: string;
  description?: string;
  severity?: Severity;
  assignedTo?: string | null;
}

// === Query params for GET /api/issues ===
export interface ListIssuesQuery {
  status?: IssueStatus;
  severity?: Severity;
  type?: IssueType;
  assignedTo?: string;
  targetType?: string;
  page?: number;
  pageSize?: number;
}
