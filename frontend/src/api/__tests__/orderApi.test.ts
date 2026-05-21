import { describe, it, expect, vi, beforeEach } from "vitest";

const getMock = vi.fn().mockResolvedValue({ data: [] });
const postMock = vi.fn().mockResolvedValue({ data: {} });
const patchMock = vi.fn().mockResolvedValue({ data: {} });
const deleteMock = vi.fn().mockResolvedValue({ data: {} });
vi.mock("@/api/httpClient", () => ({
  httpClient: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
  },
}));

import { orderApi } from "@/api/orderApi";

describe("orderApi", () => {
  beforeEach(() => {
    getMock.mockClear();
    postMock.mockClear();
    patchMock.mockClear();
    deleteMock.mockClear();
  });

  it("getOrders -> GET /orders", async () => {
    await orderApi.getOrders();
    expect(getMock).toHaveBeenCalledWith("/orders");
  });

  it("getOrderById -> GET /orders/:id", async () => {
    await orderApi.getOrderById("o-1");
    expect(getMock).toHaveBeenCalledWith("/orders/o-1");
  });

  it("createOrder -> POST /orders with body", async () => {
    await orderApi.createOrder({ title: "x" });
    expect(postMock).toHaveBeenCalledWith("/orders", { title: "x" });
  });

  it("updateOrder -> PATCH /orders/:id with body", async () => {
    await orderApi.updateOrder("o-1", { title: "y" });
    expect(patchMock).toHaveBeenCalledWith("/orders/o-1", { title: "y" });
  });

  it("deleteOrder -> DELETE /orders/:id", async () => {
    await orderApi.deleteOrder("o-1");
    expect(deleteMock).toHaveBeenCalledWith("/orders/o-1");
  });
});
