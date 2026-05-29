import type { ApiResponse } from "../types";
import { httpClient } from "@/api/httpClient";
import { AxiosError, Method } from "axios";

export async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const url = path.replace(/^\/api/, "");
  let data: unknown = undefined;
  if (init?.body != null) {
    data = typeof init.body === "string" ? JSON.parse(init.body) : init.body;
  }

  try {
    const res = await httpClient.request<ApiResponse<T>>({
      url,
      method: (init?.method as Method | undefined) ?? "GET",
      data,
      headers: init?.headers as Record<string, string> | undefined,
    });
    return res.data;
  } catch (err) {
    const axErr = err as AxiosError<{
      detail?: string;
      message?: string;
      error?: { message?: string };
    }>;
    const body = axErr.response?.data;
    const message =
      body?.detail ??
      body?.message ??
      body?.error?.message ??
      axErr.message ??
      "API request failed";
    throw new Error(message);
  }
}
