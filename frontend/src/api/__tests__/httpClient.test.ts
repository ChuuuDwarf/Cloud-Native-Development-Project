import type { AxiosAdapter, AxiosResponse } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { httpClient } from "../httpClient";

/**
 * Drives the real response interceptor (401 -> /auth/refresh -> retry) by
 * swapping the axios adapter for a programmable stub. Each call to the stub
 * resolves/rejects based on the request URL and how many times it has been hit.
 */

type AdapterHandler = (url: string, attempt: number) => Promise<AxiosResponse> | never;

function installAdapter(handler: AdapterHandler) {
  const counts = new Map<string, number>();
  const adapter: AxiosAdapter = (config) => {
    const url = config.url ?? "";
    const attempt = (counts.get(url) ?? 0) + 1;
    counts.set(url, attempt);
    return Promise.resolve().then(() => handler(url, attempt));
  };
  httpClient.defaults.adapter = adapter;
  return counts;
}

function ok(config: { url?: string } = {}): AxiosResponse {
  return {
    data: { ok: true },
    status: 200,
    statusText: "OK",
    headers: {},
    config: config as never,
  };
}

function reject401(url: string): never {
  // Shape mirrors an axios error so interceptor reads error.config / status.
  throw {
    config: { url },
    response: { status: 401, data: { error: { code: "UNAUTHORIZED", message: "x" } } },
    message: "Request failed with status code 401",
    isAxiosError: true,
  };
}

describe("httpClient response interceptor", () => {
  const originalAdapter = httpClient.defaults.adapter;

  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    httpClient.defaults.adapter = originalAdapter;
    vi.restoreAllMocks();
  });

  it("passes successful responses straight through", async () => {
    installAdapter((url) => ok({ url }));
    const res = await httpClient.get("/samples");
    expect(res.data).toEqual({ ok: true });
  });

  it("on 401 refreshes once then retries the original request", async () => {
    const counts = installAdapter((url, attempt) => {
      if (url === "/auth/refresh") return ok({ url });
      // /samples fails the first time, succeeds after refresh+retry.
      if (attempt === 1) return reject401(url);
      return ok({ url });
    });

    const res = await httpClient.get("/samples");
    expect(res.data).toEqual({ ok: true });
    expect(counts.get("/auth/refresh")).toBe(1);
    expect(counts.get("/samples")).toBe(2);
  });

  it("does not attempt refresh for auth endpoints", async () => {
    const counts = installAdapter((url) => reject401(url));
    await expect(httpClient.post("/auth/login")).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(counts.get("/auth/refresh")).toBeUndefined();
  });

  it("propagates the original 401 when refresh itself fails", async () => {
    installAdapter((url) => {
      if (url === "/auth/refresh") reject401(url);
      reject401(url);
    });

    await expect(httpClient.get("/protected")).rejects.toMatchObject({
      response: { status: 401 },
    });
  });

  it("shares a single refresh across concurrent 401s (single-flight)", async () => {
    const counts = installAdapter((url, attempt) => {
      if (url === "/auth/refresh") return ok({ url });
      if (attempt === 1) return reject401(url);
      return ok({ url });
    });

    const [a, b] = await Promise.all([httpClient.get("/a"), httpClient.get("/b")]);
    expect(a.data).toEqual({ ok: true });
    expect(b.data).toEqual({ ok: true });
    // Two distinct endpoints 401 concurrently, but only ONE refresh fires.
    expect(counts.get("/auth/refresh")).toBe(1);
  });
});
