import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useResourceQuery } from "../useResourceQuery";

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("useResourceQuery", () => {
  it("returns fetched data and not offline on success", async () => {
    const queryFn = vi.fn().mockResolvedValue({ value: 42 });
    const { result } = renderHook(() => useResourceQuery(["k-success"], queryFn, { value: 0 }), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.offline).toBe(false);
  });

  it("falls back to demo data with offline=true on error", async () => {
    const queryFn = vi.fn().mockRejectedValue(new Error("boom"));
    const fallback = { value: -1 };
    const { result } = renderHook(() => useResourceQuery(["k-error"], queryFn, fallback), {
      wrapper: makeWrapper(),
    });

    // useResourceQuery sets retry: 1 internally, so the error settles after a
    // retry + backoff — give waitFor headroom beyond the default 1s.
    await waitFor(() => expect(result.current.offline).toBe(true), { timeout: 5000 });
    expect(result.current.data).toEqual(fallback);
    expect(result.current.loading).toBe(false);
  });

  it("exposes a reload that re-invokes the query function", async () => {
    const queryFn = vi.fn().mockResolvedValue({ value: 1 });
    const { result } = renderHook(() => useResourceQuery(["k-reload"], queryFn, { value: 0 }), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    const callsBefore = queryFn.mock.calls.length;
    result.current.reload();
    await waitFor(() => expect(queryFn.mock.calls.length).toBeGreaterThan(callsBefore));
  });
});
