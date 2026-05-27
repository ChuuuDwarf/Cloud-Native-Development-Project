"use client";

import { useQuery } from "@tanstack/react-query";

export interface ResourceResult<T> {
  /** Live data when the request succeeds, otherwise the offline fallback. */
  data: T;
  loading: boolean;
  /** True when the request failed and we fell back to the demo data. */
  offline: boolean;
  reload: () => void;
}

/**
 * TanStack Query wrapper that preserves the old `lib/useResource` contract:
 * fetch via the service `queryFn`, and on error fall back to demo `fallback`
 * data with `offline = true` so pages still render without a live backend.
 *
 * Replaces `@/lib/useResource` — same `{ data, loading, offline, reload }`
 * shape, but with React Query caching/invalidation underneath.
 */
export function useResourceQuery<T>(
  queryKey: readonly unknown[],
  queryFn: () => Promise<T>,
  fallback: T,
  options?: { refetchInterval?: number }
): ResourceResult<T> {
  const query = useQuery({ queryKey, queryFn, retry: 1, ...options });

  return {
    data: query.isError ? fallback : (query.data ?? fallback),
    loading: query.isLoading,
    offline: query.isError,
    reload: () => {
      void query.refetch();
    },
  };
}
