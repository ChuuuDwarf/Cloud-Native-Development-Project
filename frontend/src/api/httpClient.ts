import axios from "axios";

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

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (process.env.NODE_ENV !== "production") {
      // Surfaces backend ErrorResponse envelopes in the console during dev.
      console.error(
        "API request failed:",
        error?.response?.status,
        error?.response?.data || error.message,
      );
    }
    return Promise.reject(error);
  },
);

export type ApiErrorResponse = {
  error: { code: string; message: string; details?: unknown };
};
