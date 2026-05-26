import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
export type { Machine, MachinePayload, MachineStatus } from "@/types/machines";
import type { Machine, MachinePayload, MachineStatus } from "@/types/machines";

export const machinesApi = {
  async list(): Promise<Machine[]> {
    const res = await httpClient.get<PageResponse<Machine>>("/machines");
    return res.data.items;
  },

  async create(payload: MachinePayload): Promise<Machine> {
    const res = await httpClient.post<ApiResponse<Machine>>("/machines", payload);
    return res.data.data;
  },

  async update(machineId: string, payload: MachinePayload): Promise<Machine> {
    const res = await httpClient.patch<ApiResponse<Machine>>(`/machines/${machineId}`, payload);
    return res.data.data;
  },

  async updateStatus(machineId: string, status: MachineStatus): Promise<Machine> {
    const res = await httpClient.patch<ApiResponse<Machine>>(`/machines/${machineId}/status`, {
      status,
    });
    return res.data.data;
  },
};
