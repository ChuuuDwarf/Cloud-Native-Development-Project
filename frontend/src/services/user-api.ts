import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
import type {
  CreateUserPayload,
  ListUsersQuery,
  UpdateUserPayload,
  UserResponse,
} from "@/types/user";

export const userApi = {
  async list(query: ListUsersQuery = {}): Promise<PageResponse<UserResponse>> {
    const res = await httpClient.get<PageResponse<UserResponse>>("/users", {
      params: query,
    });
    return res.data;
  },

  async getById(id: string): Promise<UserResponse> {
    const res = await httpClient.get<ApiResponse<UserResponse>>(`/users/${id}`);
    return res.data.data;
  },

  async create(payload: CreateUserPayload): Promise<UserResponse> {
    const res = await httpClient.post<ApiResponse<UserResponse>>(
      "/users",
      payload,
    );
    return res.data.data;
  },

  async update(id: string, payload: UpdateUserPayload): Promise<UserResponse> {
    const res = await httpClient.patch<ApiResponse<UserResponse>>(
      `/users/${id}`,
      payload,
    );
    return res.data.data;
  },
};
