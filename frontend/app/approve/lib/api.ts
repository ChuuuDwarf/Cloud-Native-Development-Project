import type { ApiResponse } from "../types";

const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
  /\/api\/?$/,
  ""
);

export async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "API request failed");
  }

  return payload as ApiResponse<T>;
}
