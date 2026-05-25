export function getErrorMessage(error: unknown, fallback = "操作失敗") {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  if (typeof error === "string" && error.trim()) {
    return error;
  }

  return fallback;
}

export function logClientError(context: string, error: unknown) {
  if (process.env.NODE_ENV !== "production") {
    console.error(`${context}:`, error);
  }
}
