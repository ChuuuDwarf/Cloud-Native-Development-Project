import { httpClient } from "@/api/httpClient";
import type { ApiResponse } from "@/types/api";
import type { MeResponse } from "@/types/user";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  userId: string;
  name: string;
  email: string;
  role: string;
  permissions: string[];
}

export const authApi = {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    const res = await httpClient.post<ApiResponse<LoginResponse>>(
      "/auth/login",
      payload,
    );
    return res.data.data;
  },

  async logout(): Promise<void> {
    await httpClient.post("/auth/logout");
  },

  async me(): Promise<MeResponse> {
    const res = await httpClient.get<ApiResponse<MeResponse>>("/me");
    return res.data.data;
  },
};
