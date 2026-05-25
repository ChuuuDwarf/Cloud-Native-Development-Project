import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
export type { AssignDispatchPayload, CreateDispatchPayload, Dispatch, Strategy, WipStatus } from "@/types/dispatches";
import type { AssignDispatchPayload, CreateDispatchPayload, Dispatch, Strategy } from "@/types/dispatches";

export const dispatchesApi = {
  async list(): Promise<Dispatch[]> {
    const res = await httpClient.get<PageResponse<Dispatch>>("/dispatches");
    return res.data.items;
  },

  async create(payload: CreateDispatchPayload): Promise<Dispatch> {
    const res = await httpClient.post<ApiResponse<Dispatch>>(
      "/dispatches",
      payload,
    );
    return res.data.data;
  },

  async suggest(strategy: Strategy): Promise<Dispatch[]> {
    const res = await httpClient.post<ApiResponse<Dispatch[]>>(
      "/dispatches/suggest",
      { strategy },
    );
    return res.data.data;
  },

  async replan(reason: string, strategy: Strategy): Promise<Dispatch[]> {
    const res = await httpClient.post<ApiResponse<Dispatch[]>>(
      "/dispatches/replan",
      { reason, strategy },
    );
    return res.data.data;
  },

  async assign(
    dispatchId: string,
    payload: AssignDispatchPayload,
  ): Promise<Dispatch> {
    const res = await httpClient.post<ApiResponse<Dispatch>>(
      `/dispatches/${dispatchId}/assign`,
      payload,
    );
    return res.data.data;
  },
};
