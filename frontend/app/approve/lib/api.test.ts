import { beforeEach, describe, expect, it, vi } from "vitest";

const requestMock = vi.fn();
vi.mock("@/api/httpClient", () => ({
  httpClient: { request: (...a: unknown[]) => requestMock(...a) },
}));

import { requestJson } from "./api";

describe("approve/lib/api requestJson", () => {
  beforeEach(() => {
    requestMock.mockReset();
  });

  it("strips /api, defaults to GET, returns response data", async () => {
    requestMock.mockResolvedValue({ data: { data: [1, 2], message: "success" } });
    const out = await requestJson("/api/orders/approvals");
    expect(requestMock).toHaveBeenCalledWith({
      url: "/orders/approvals",
      method: "GET",
      data: undefined,
      headers: undefined,
    });
    expect(out).toEqual({ data: [1, 2], message: "success" });
  });

  it("parses string body and forwards method", async () => {
    requestMock.mockResolvedValue({ data: { data: null, message: "success" } });
    await requestJson("/api/orders/1/approve", {
      method: "POST",
      body: JSON.stringify({ reason: "ok" }),
    });
    expect(requestMock).toHaveBeenCalledWith(
      expect.objectContaining({ url: "/orders/1/approve", method: "POST", data: { reason: "ok" } })
    );
  });

  it("surfaces the most specific error message available", async () => {
    requestMock.mockRejectedValue({ response: { data: { detail: "需特批" } } });
    await expect(requestJson("/api/orders/1/approve")).rejects.toThrow("需特批");

    requestMock.mockRejectedValue({});
    await expect(requestJson("/api/orders/1/approve")).rejects.toThrow("API request failed");
  });
});
