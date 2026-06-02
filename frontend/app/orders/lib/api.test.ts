import { beforeEach, describe, expect, it, vi } from "vitest";

const requestMock = vi.fn();
vi.mock("@/api/httpClient", () => ({
  httpClient: { request: (...a: unknown[]) => requestMock(...a) },
}));

import { requestJson } from "./api";

describe("orders/lib/api requestJson", () => {
  beforeEach(() => {
    requestMock.mockReset();
  });

  it("strips the /api prefix and defaults to GET", async () => {
    requestMock.mockResolvedValue({ data: { data: { ok: 1 }, message: "success" } });
    const out = await requestJson("/api/orders");
    expect(requestMock).toHaveBeenCalledWith({
      url: "/orders",
      method: "GET",
      data: undefined,
      headers: undefined,
    });
    expect(out).toEqual({ data: { ok: 1 }, message: "success" });
  });

  it("parses a string JSON body and forwards method + headers", async () => {
    requestMock.mockResolvedValue({ data: { data: null, message: "success" } });
    await requestJson("/api/orders", {
      method: "POST",
      body: JSON.stringify({ name: "x" }),
      headers: { "X-Test": "1" },
    });
    expect(requestMock).toHaveBeenCalledWith({
      url: "/orders",
      method: "POST",
      data: { name: "x" },
      headers: { "X-Test": "1" },
    });
  });

  it("passes a non-string body through unchanged", async () => {
    requestMock.mockResolvedValue({ data: { data: null, message: "success" } });
    const body = { a: 1 } as unknown as BodyInit;
    await requestJson("/api/orders", { method: "PUT", body });
    expect(requestMock).toHaveBeenCalledWith(
      expect.objectContaining({ data: { a: 1 }, method: "PUT" })
    );
  });

  it("extracts error message from response body.detail", async () => {
    requestMock.mockRejectedValue({ response: { data: { detail: "壞掉了" } }, message: "axios" });
    await expect(requestJson("/api/orders")).rejects.toThrow("壞掉了");
  });

  it("falls back through message and error.message", async () => {
    requestMock.mockRejectedValue({ response: { data: { message: "中層訊息" } } });
    await expect(requestJson("/api/orders")).rejects.toThrow("中層訊息");

    requestMock.mockRejectedValue({ response: { data: { error: { message: "巢狀訊息" } } } });
    await expect(requestJson("/api/orders")).rejects.toThrow("巢狀訊息");
  });

  it("falls back to axios message then a generic default", async () => {
    requestMock.mockRejectedValue({ message: "Network Error" });
    await expect(requestJson("/api/orders")).rejects.toThrow("Network Error");

    requestMock.mockRejectedValue({});
    await expect(requestJson("/api/orders")).rejects.toThrow("API request failed");
  });
});
