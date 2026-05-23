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

  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : typeof payload === "object" && payload && "message" in payload
          ? String((payload as { message: unknown }).message)
          : typeof payload === "object" && payload && "error" in payload
            ? String(
                (payload as { error?: { message?: unknown } }).error?.message ??
                  "API request failed"
              )
            : "API request failed";

    throw new Error(message);
  }

  return payload as ApiResponse<T>;
}
