import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
import type { Wip } from "@/types/lab";

/** Payload for 上機登記. */
export interface CheckInPayload {
  operator: string;
  machineId: string;
  recipe: string;
}

/** Payload for 下機登記 / 結果確認 (both reuse the operator field). */
export interface CheckOutPayload {
  operator: string;
  note?: string | null;
}

/** Payload for 上傳結果. */
export interface ResultPayload {
  note: string;
  rawDataUrl?: string | null;
  dataVerified: boolean;
}

/** Payload for 主管審核中止申請. */
export interface AbortReviewPayload {
  approve: boolean;
  note?: string | null;
}

/**
 * 實驗執行 API client — wraps `/experiment-runs` (baseURL already adds `/api`).
 * Cookie auth via httpClient; the old X-Role header is gone (server reads the
 * JWT cookie). The list endpoint returns the standard `PageResponse`
 * (`{ items, page, pageSize, total }`); action endpoints return
 * `ApiResponse<T>` (`{ data, message }`).
 */
export interface Operator {
  name: string;
  role: string;
}

export const experimentsApi = {
  async list(): Promise<Wip[]> {
    const res = await httpClient.get<PageResponse<Wip>>("/experiment-runs");
    return res.data.items;
  },

  /** 此 WIP 所屬實驗室的人員/主管（上機登記操作人下拉）。 */
  async getOperators(wipId: string): Promise<Operator[]> {
    const res = await httpClient.get<ApiResponse<Operator[]>>(
      `/experiment-runs/${wipId}/operators`
    );
    return res.data.data;
  },

  async checkIn(wipId: string, payload: CheckInPayload): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(
      `/experiment-runs/${wipId}/check-in`,
      payload
    );
    return res.data.data;
  },

  async checkOut(wipId: string, payload: CheckOutPayload): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(
      `/experiment-runs/${wipId}/check-out`,
      payload
    );
    return res.data.data;
  },

  async updateProgress(wipId: string, progress: number): Promise<Wip> {
    const res = await httpClient.patch<ApiResponse<Wip>>(`/experiment-runs/${wipId}/progress`, {
      progress,
    });
    return res.data.data;
  },

  async uploadResult(wipId: string, payload: ResultPayload): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(
      `/experiment-runs/${wipId}/result`,
      payload
    );
    return res.data.data;
  },

  async verify(wipId: string, payload: CheckOutPayload): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(
      `/experiment-runs/${wipId}/verify`,
      payload
    );
    return res.data.data;
  },

  async confirm(wipId: string, payload: CheckOutPayload): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(
      `/experiment-runs/${wipId}/confirm`,
      payload
    );
    return res.data.data;
  },

  async abortRequest(wipId: string, reason: string): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(`/experiment-runs/${wipId}/abort-request`, {
      reason,
    });
    return res.data.data;
  },

  async abortReview(wipId: string, payload: AbortReviewPayload): Promise<Wip> {
    const res = await httpClient.post<ApiResponse<Wip>>(
      `/experiment-runs/${wipId}/abort-review`,
      payload
    );
    return res.data.data;
  },

  /** 模擬機台回報「完成」訊號 (POST /experiment-runs/{id}/machine-signal). */
  async machineSignal(wipId: string): Promise<unknown> {
    const res = await httpClient.post<ApiResponse<unknown>>(
      `/experiment-runs/${wipId}/machine-signal`
    );
    return res.data.data;
  },
};
