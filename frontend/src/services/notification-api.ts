import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
import type {
  ListNotificationsQuery,
  MarkReadPayload,
  MarkReadResult,
  NotificationResponse,
} from "@/types/notification";

export const notificationApi = {
  async list(
    query: ListNotificationsQuery = {},
  ): Promise<PageResponse<NotificationResponse>> {
    const res = await httpClient.get<PageResponse<NotificationResponse>>(
      "/notifications",
      { params: query },
    );
    return res.data;
  },

  async getById(id: string): Promise<NotificationResponse> {
    const res = await httpClient.get<ApiResponse<NotificationResponse>>(
      `/notifications/${id}`,
    );
    return res.data.data;
  },

  async markRead(payload: MarkReadPayload): Promise<MarkReadResult> {
    const res = await httpClient.post<ApiResponse<MarkReadResult>>(
      "/notifications/actions",
      payload,
    );
    return res.data.data;
  },
};
