import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
import type {
  CreateIssuePayload,
  IssueResponse,
  ListIssuesQuery,
  UpdateIssuePayload,
} from "@/types/issue";

export const issueApi = {
  async list(query: ListIssuesQuery = {}): Promise<PageResponse<IssueResponse>> {
    const res = await httpClient.get<PageResponse<IssueResponse>>("/issues", {
      params: query,
    });
    return res.data;
  },

  async getById(id: string): Promise<IssueResponse> {
    const res = await httpClient.get<ApiResponse<IssueResponse>>(`/issues/${id}`);
    return res.data.data;
  },

  async create(payload: CreateIssuePayload): Promise<IssueResponse> {
    const res = await httpClient.post<ApiResponse<IssueResponse>>("/issues", payload);
    return res.data.data;
  },

  async update(id: string, payload: UpdateIssuePayload): Promise<IssueResponse> {
    const res = await httpClient.patch<ApiResponse<IssueResponse>>(`/issues/${id}`, payload);
    return res.data.data;
  },
};
