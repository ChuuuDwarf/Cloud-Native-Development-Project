import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const requestJsonMock = vi.fn();
const getByIdMock = vi.fn();
let authValue: { user: { id: string; name: string; departmentId: string; role: string } | null };

vi.mock("../lib/api", () => ({
  requestJson: (...a: unknown[]) => requestJsonMock(...a),
}));
vi.mock("@/services/user-api", () => ({
  userApi: { getById: (...a: unknown[]) => getByIdMock(...a) },
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authValue,
}));

import { useOrdersPage } from "./useOrdersPage";
import type { Order } from "../types";

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 1,
    orderNo: "ORD-1",
    applicantId: "u1",
    departmentId: "d1",
    applyDate: "2026-01-01T00:00:00",
    status: "draft",
    priority: "normal",
    totalItems: 1,
    createdAt: "2026-01-01T00:00:00",
    updatedAt: "2026-01-01T00:00:00",
    items: [
      {
        id: 11,
        sampleId: "SMP-1",
        labId: "lab-1",
        experimentId: "exp-1",
        targetGroup: "G1",
        target: 1,
        check: false,
      },
    ],
    ...overrides,
  };
}

const master = {
  departments: [{ id: "d1", name: "部門一" }],
  labs: [{ id: "lab-1", name: "Lab 1" }],
  experiments: [{ id: "exp-1", name: "E1", labId: "lab-1" }],
};

function routeRequests(opts: { orders?: Order[]; createRejects?: boolean } = {}) {
  requestJsonMock.mockImplementation((path: string, init?: { method?: string }) => {
    if (path === "/api/master-data") return Promise.resolve({ data: master });
    if (path === "/api/quotas") return Promise.resolve({ data: [{ labId: "lab-1", used: 1 }] });
    if (path.startsWith("/api/orders/quota-check"))
      return Promise.resolve({ data: { exceeded: false } });
    if (/\/api\/orders\/\d+\/history$/.test(path))
      return Promise.resolve({ data: [{ actorId: "a1" }] });
    if (/\/api\/orders\/\d+\/actions$/.test(path))
      return Promise.resolve({ data: { id: 1, status: "pending_approval" } });
    if (/\/api\/orders\/\d+\/dependencies\/next/.test(path))
      return Promise.resolve({ data: null });
    if (/\/api\/orders\/\d+$/.test(path)) {
      if (init?.method === "DELETE") return Promise.resolve({ data: { id: 1 } });
      return Promise.resolve({ data: makeOrder() });
    }
    if (path === "/api/orders" || path.startsWith("/api/orders?")) {
      if (init?.method === "POST") {
        return opts.createRejects
          ? Promise.reject(new Error("建立失敗"))
          : Promise.resolve({ data: makeOrder({ id: 99, orderNo: "ORD-99" }) });
      }
      return Promise.resolve({ data: opts.orders ?? [makeOrder()] });
    }
    return Promise.resolve({ data: [] });
  });
}

describe("useOrdersPage", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
    getByIdMock.mockReset();
    getByIdMock.mockResolvedValue({ name: "某人" });
    authValue = { user: { id: "u1", name: "王小明", departmentId: "d1", role: "plant_user" } };
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  async function mount(opts?: { orders?: Order[] }) {
    routeRequests(opts);
    const view = renderHook(() => useOrdersPage());
    await waitFor(() => expect(view.result.current.orders.length).toBeGreaterThan(0));
    return view;
  }

  it("loads master data, orders, and quotas on mount", async () => {
    const { result } = await mount();
    expect(result.current.masterData.labs).toHaveLength(1);
    expect(result.current.orders).toHaveLength(1);
    expect(result.current.quotaSettings).toEqual([{ labId: "lab-1", used: 1 }]);
  });

  it("plant_user only sees their own orders", async () => {
    const { result } = await mount({
      orders: [makeOrder({ id: 1, applicantId: "u1" }), makeOrder({ id: 2, applicantId: "other" })],
    });
    expect(result.current.orders.map((o) => o.id)).toEqual([1]);
  });

  it("computes statusCounts and applies the active status filter", async () => {
    const { result } = await mount({
      orders: [
        makeOrder({ id: 1, status: "draft", applicantId: "u1" }),
        makeOrder({ id: 2, status: "approved", applicantId: "u1" }),
      ],
    });
    expect(result.current.statusCounts.all).toBe(2);
    expect(result.current.statusCounts.draft).toBe(1);

    act(() => result.current.setActiveStatusFilter("approved"));
    await waitFor(() => expect(result.current.filteredOrders.map((o) => o.id)).toEqual([2]));
  });

  it("openCreateOrder opens the form and resetForm seeds a default item", async () => {
    const { result } = await mount();
    act(() => result.current.openCreateOrder());
    expect(result.current.formModalOpen).toBe(true);
    expect(result.current.items).toHaveLength(1);
    act(() => result.current.closeFormModal());
    expect(result.current.formModalOpen).toBe(false);
  });

  it("startEditOrder rejects non-draft/returned orders", async () => {
    const { result } = await mount();
    act(() => result.current.startEditOrder(makeOrder({ status: "approved" })));
    expect(result.current.modal).toMatchObject({ title: "不可編輯" });
  });

  it("startEditOrder loads a draft order into the form", async () => {
    const { result } = await mount();
    act(() => result.current.startEditOrder(makeOrder({ id: 7, status: "draft" })));
    expect(result.current.editingOrderId).toBe(7);
    expect(result.current.items[0].sampleId).toBe("SMP-1");
    expect(result.current.formModalOpen).toBe(true);
  });

  it("getDetail and getHistory open the matching modals", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.getDetail(1);
    });
    expect(result.current.modal).toMatchObject({ type: "detail" });
    await act(async () => {
      await result.current.getHistory(1);
    });
    expect(result.current.modal).toMatchObject({ type: "history" });
  });

  it("doAction posts and shows a success modal", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.doAction(makeOrder(), "submit");
    });
    expect(result.current.modal).toMatchObject({ type: "message", title: "操作成功" });
  });

  it("deleteOrder rejects non-draft and confirms before deleting drafts", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.deleteOrder(makeOrder({ status: "approved" }));
    });
    expect(result.current.modal).toMatchObject({ title: "不可刪除" });

    vi.spyOn(window, "confirm").mockReturnValue(true);
    await act(async () => {
      await result.current.deleteOrder(makeOrder({ status: "draft" }));
    });
    expect(result.current.modal).toMatchObject({ title: "刪除成功" });
  });

  it("deleteOrder aborts when the confirm dialog is cancelled", async () => {
    const { result } = await mount();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    await act(async () => {
      await result.current.deleteOrder(makeOrder({ status: "draft" }));
    });
    // no success/failure modal because the user cancelled
    expect(result.current.modal).toMatchObject({ type: "none" });
  });

  it("createOrder validates an incomplete form before submitting", async () => {
    const { result } = await mount();
    act(() => result.current.openCreateOrder());
    await act(async () => {
      await result.current.createOrder();
    });
    // default item has empty lab/experiment -> validation message modal
    expect(result.current.modal.type).toBe("message");
    // it should not have POSTed an order
    expect(requestJsonMock.mock.calls.some(([p, i]) => p === "/api/orders" && i?.method === "POST")).toBe(
      false
    );
  });

  it("addSample / removeItem manage form items", async () => {
    const { result } = await mount();
    act(() => result.current.openCreateOrder());
    act(() => result.current.addSample());
    expect(result.current.items).toHaveLength(2);
    act(() => result.current.removeItem(1));
    expect(result.current.items).toHaveLength(1);
  });

  it("saveCurrentTemplate and applyTemplate manage local templates", async () => {
    const { result } = await mount();
    act(() => result.current.openCreateOrder());
    act(() => {
      result.current.updateDependencyItems(result.current.sampleGroups[0], [
        {
          sampleId: "SMP-1",
          sampleName: "x",
          labId: "lab-1",
          experimentId: "exp-1",
          targetGroup: "G1",
          target: 1,
          check: false,
        },
      ]);
      result.current.setTemplateName("樣板A");
    });
    act(() => result.current.saveCurrentTemplate());
    await waitFor(() => expect(result.current.templates.length).toBeGreaterThan(0));

    const tid = result.current.templates[0].id;
    act(() => result.current.applyTemplate(tid));
    expect(result.current.selectedTemplateId).toBe(tid);
  });
});
