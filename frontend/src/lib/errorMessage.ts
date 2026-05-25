import type { ApiErrorBody } from "@/types/api";

/**
 * Extract a human-readable message from a failed request.
 *
 * The backend returns business errors as `{ error: { code, message } }`
 * (see `ApiErrorBody`), so for a 409/422 we want to surface that Chinese
 * message (e.g. 「數據完整性尚未驗證，無法確認結果」) rather than axios's
 * generic "Request failed with status code 422". Falls back to the axios
 * error message, then a generic hint.
 */
export function errorMessage(e: unknown): string {
  const res = (e as { response?: { data?: ApiErrorBody } } | undefined)
    ?.response;
  const backend = res?.data?.error?.message;
  if (backend) return backend;
  if (e instanceof Error && e.message) return e.message;
  return "操作失敗，請確認後端是否啟動";
}
