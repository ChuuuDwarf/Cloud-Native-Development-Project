import axios, { type AxiosRequestConfig } from "axios";

export const httpClient = axios.create({
  // NEXT_PUBLIC_* env vars in Next.js are baked at build time, so this is
  // read once during `next build`. Pass it as a Docker build-arg in CI/prod;
  // for local `next dev` the runtime env var is honored.
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  timeout: 10000,
  // CRITICAL: the backend sets a httpOnly cookie at /api/auth/login and reads
  // it on every authenticated request. Without withCredentials, the browser
  // won't send the cookie cross-origin (browser → http://localhost:8000 from
  // http://localhost:3000).
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// 401 → refresh → retry (Sprint 7)
// ---------------------------------------------------------------------------
//
// Access token TTL is 60min. When it expires mid-session, every protected
// endpoint starts returning 401. We catch the first such 401, call
// POST /auth/refresh once, then retry the original request transparently.
//
// Single-flight: if multiple requests fire concurrently (e.g. dashboard
// loads 4 widgets in parallel) and all 401, only ONE refresh call goes
// out — the rest await the same in-flight promise. Without this we'd
// hammer the server with N parallel refresh calls and end up with cookie
// races (later refresh issues a new pair, earlier already used the
// half-stale jar).
//
// Retry guard: each request config gets a one-shot _retry flag so a
// genuinely-401 endpoint (e.g. /auth/login with wrong password) doesn't
// loop forever.

type RetryableConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<void> | null = null;

function isAuthEndpoint(url: string): boolean {
  // Don't try to refresh from inside an auth flow — login / refresh / logout
  // 401-ing has business meaning, not "token expired".
  return (
    url.includes("/auth/login") || url.includes("/auth/refresh") || url.includes("/auth/logout")
  );
}

httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetryableConfig | undefined;
    const status: number | undefined = error?.response?.status;
    const url: string = original?.url ?? "";

    if (status === 401 && original && !original._retry && !isAuthEndpoint(url)) {
      original._retry = true;
      // Single-flight: share one refresh promise across concurrent 401s.
      refreshPromise ??= httpClient
        .post("/auth/refresh")
        .then(() => undefined)
        .finally(() => {
          refreshPromise = null;
        });

      try {
        await refreshPromise;
        return httpClient(original);
      } catch {
        // Refresh itself failed (no cookie, expired, or token-type mismatch).
        // Fall through so the original 401 reaches AuthContext, which
        // setUser(null) and redirects to /login.
      }
    }

    if (process.env.NODE_ENV !== "production") {
      // Surfaces backend ErrorResponse envelopes in the console during dev.
      console.error("API request failed:", status, error?.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);

export type ApiErrorResponse = {
  error: { code: string; message: string; details?: unknown };
};
