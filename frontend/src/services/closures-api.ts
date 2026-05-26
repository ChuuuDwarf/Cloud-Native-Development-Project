import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
import type { ClosureCheck, StorageItem } from "@/types/lab";

/** Shared payload for the storage / close steps (入庫 / 出庫 / 結案). */
export interface CloseStepPayload {
  operator?: string | null;
  note?: string | null;
}

/**
 * 結單與倉儲 API client — wraps `/closures` (baseURL already adds `/api`).
 * Cookie auth via httpClient; the old X-Role header is dropped. The list
 * endpoints return the standard `PageResponse` (`{ items, page, pageSize,
 * total }`); the action endpoints return `ApiResponse<T>` (`{ data, message }`).
 */
export const closuresApi = {
  async list(): Promise<ClosureCheck[]> {
    const res = await httpClient.get<PageResponse<ClosureCheck>>("/closures");
    return res.data.items;
  },

  /** 倉儲取件清單 (GET /closures/storage, optional status filter). */
  async listStorage(status?: string): Promise<StorageItem[]> {
    const res = await httpClient.get<PageResponse<StorageItem>>(
      "/closures/storage",
      status ? { params: { status } } : undefined
    );
    return res.data.items;
  },

  /** 轉待取件 (結單條件全部滿足後). */
  async toPickup(orderId: string): Promise<ClosureCheck> {
    const res = await httpClient.post<ApiResponse<ClosureCheck>>(`/closures/${orderId}/to-pickup`);
    return res.data.data;
  },

  /** 樣品入庫. */
  async inbound(orderId: string, payload: CloseStepPayload): Promise<StorageItem> {
    const res = await httpClient.post<ApiResponse<StorageItem>>(
      `/closures/${orderId}/inbound`,
      payload
    );
    return res.data.data;
  },

  /** 樣品出庫取件. */
  async outbound(orderId: string, payload: CloseStepPayload): Promise<StorageItem> {
    const res = await httpClient.post<ApiResponse<StorageItem>>(
      `/closures/${orderId}/outbound`,
      payload
    );
    return res.data.data;
  },

  /** 委託單結案 (使用者取件後). */
  async close(orderId: string, payload: CloseStepPayload): Promise<ClosureCheck> {
    const res = await httpClient.post<ApiResponse<ClosureCheck>>(
      `/closures/${orderId}/close`,
      payload
    );
    return res.data.data;
  },
};
