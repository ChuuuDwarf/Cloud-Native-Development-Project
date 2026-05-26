import type {
  NotificationChannel,
  NotificationStatus,
  Severity,
} from "@/constants/enums";

// === API response shape (matches backend NotificationRead) ===
export interface NotificationResponse {
  id: string;
  recipientId: string;
  labId: string;
  sourceType: string;
  sourceId: string;
  title: string;
  body: string;
  severity: Severity;
  channel: NotificationChannel;
  status: NotificationStatus;
  readAt: string | null;
  createdAt: string;
  updatedAt: string;
}

// === Query params for GET /api/notifications ===
export interface ListNotificationsQuery {
  status?: NotificationStatus;
  severity?: Severity;
  channel?: NotificationChannel;
  sourceType?: string;
  page?: number;
  pageSize?: number;
}

// === Request / response for POST /api/notifications/actions ===
export interface MarkReadPayload {
  ids: string[];
}

export interface MarkReadResult {
  markedCount: number;
  skippedIds: string[];
}
