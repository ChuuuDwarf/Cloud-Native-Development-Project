import { QueryClient } from "@tanstack/react-query";

// Single QueryClient for the whole app. Default options tuned for a LIMS:
// - moderate staleTime so dashboards don't refetch on every focus
// - retries off for 401/403/4xx (no point retrying an auth failure)
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error: unknown) => {
        const status = (error as { response?: { status?: number } })?.response?.status;
        if (status && status >= 400 && status < 500) return false;
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
