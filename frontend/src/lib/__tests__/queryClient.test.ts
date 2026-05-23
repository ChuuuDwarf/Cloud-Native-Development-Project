import { describe, it, expect } from "vitest";
import { queryClient } from "@/lib/queryClient";

describe("queryClient", () => {
  it("exports a configured QueryClient instance", () => {
    const opts = queryClient.getDefaultOptions();
    expect(opts.queries?.staleTime).toBe(30_000);
    expect(opts.queries?.refetchOnWindowFocus).toBe(false);
    expect(opts.mutations?.retry).toBe(false);
  });

  it("query retry returns false for 4xx errors and limits other retries to 2", () => {
    const opts = queryClient.getDefaultOptions();
    const retry = opts.queries?.retry as (
      failureCount: number,
      error: unknown,
    ) => boolean;
    // 401 -> no retry
    expect(retry(0, { response: { status: 401 } })).toBe(false);
    expect(retry(0, { response: { status: 404 } })).toBe(false);
    // 500 -> retry up to 2
    expect(retry(0, { response: { status: 500 } })).toBe(true);
    expect(retry(1, { response: { status: 500 } })).toBe(true);
    expect(retry(2, { response: { status: 500 } })).toBe(false);
    // unknown error shape -> retry up to 2
    expect(retry(0, new Error("network"))).toBe(true);
  });
});
