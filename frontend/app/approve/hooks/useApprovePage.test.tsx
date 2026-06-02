import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const requestJsonMock = vi.fn();
const getByIdMock = vi.fn();
let authValue: { user: unknown; hasPermission: (p: string) => boolean };

vi.mock("../lib/api", () => ({
  requestJson: (...a: unknown[]) => requestJsonMock(...a),
}));
vi.mock("@/services/user-api", () => ({
  userApi: { getById: (...a: unknown[]) => getByIdMock(...a) },
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authValue,
}));

import { useApprovePage } from "./useApprovePage";
import type { Order } from "../types";

const pendingOrder: Order = {
  id: 1,
  orderNo: "ORD-1",
  applicantId: "applicant-1",
  departmentId: "d1",
  applyDate: "2026-01-01T00:00:00",
  status: "pending_approval",
  priority: "normal",
  totalItems: 1,
  createdAt: "2026-01-01T00:00:00",
  updatedAt: "2026-01-01T00:00:00",
  items: [
    {
      id: 11,
      sampleId: "S1",
      labId: "lab-1",
      experimentId: "e1",
      targetGroup: "G1",
      target: 1,
      check: false,
      approvedBy: "approver-9",
    },
  ],
};

// Route requestJson by URL so mount-time loads + actions all resolve.
function routeRequests(overrides: Record<string, unknown> = {}) {
  requestJsonMock.mockImplementation((path: string) => {
    if (path.startsWith("/api/orders?status=pending_approval")) {
      return Promise.resolve({ data: overrides.orders ?? [pendingOrder] });
    }
    if (path === "/api/master-data") {
      return Promise.resolve({
        data: { departments: [{ id: "d1" }], labs: [{ id: "lab-1" }], experiments: [] },
      });
    }
    if (/\/api\/orders\/\d+\/history$/.test(path)) {
      return Promise.resolve({ data: overrides.history ?? [{ actorId: "actor-x" }] });
    }
    if (/\/api\/orders\/\d+\/actions$/.test(path)) {
      return overrides.actionRejects
        ? Promise.reject(new Error("簽核失敗"))
        : Promise.resolve({ data: { id: 1, status: "approved" } });
    }
    if (/\/api\/orders\/\d+$/.test(path)) {
      return Promise.resolve({ data: overrides.detail ?? pendingOrder });
    }
    return Promise.resolve({ data: [] });
  });
}

const adminUser = {
  id: "approver-1",
  permissions: ["*"],
  labId: "lab-1",
};

describe("useApprovePage", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
    getByIdMock.mockReset();
    getByIdMock.mockResolvedValue({ name: "某使用者" });
    authValue = { user: adminUser, hasPermission: () => true };
  });
  afterEach(() => vi.restoreAllMocks());

  async function mount() {
    routeRequests();
    const view = renderHook(() => useApprovePage());
    await waitFor(() => expect(view.result.current.orders).toHaveLength(1));
    return view;
  }

  it("loads pending orders + master data on mount and derives actorLabIds from items (wildcard)", async () => {
    const { result } = await mount();
    expect(result.current.log).toContain("已載入 1 筆");
    expect(result.current.masterData.labs).toEqual([{ id: "lab-1" }]);
    expect(result.current.actorLabIds).toEqual(["lab-1"]);
    expect(result.current.canApprove).toBe(true);
  });

  it("uses only the user's labId when not a wildcard", async () => {
    authValue = { user: { ...adminUser, permissions: ["orders:approve"] }, hasPermission: () => true };
    const { result } = await mount();
    expect(result.current.actorLabIds).toEqual(["lab-1"]);
  });

  it("getDetail opens a detail modal", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.getDetail(1);
    });
    expect(result.current.modal).toMatchObject({ type: "detail", order: { id: 1 } });
  });

  it("getHistory opens a history modal", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.getHistory(1);
    });
    expect(result.current.modal).toMatchObject({ type: "history" });
  });

  it("approve without quota override submits immediately and reloads", async () => {
    const { result } = await mount();
    await act(async () => {
      result.current.openReasonModal(pendingOrder, "approve");
    });
    await waitFor(() =>
      expect(result.current.modal).toMatchObject({ type: "message", title: "簽核操作成功" })
    );
  });

  it("return/reject open the reason modal instead of submitting", async () => {
    const { result } = await mount();
    act(() => result.current.openReasonModal(pendingOrder, "return"));
    expect(result.current.reasonModal).toMatchObject({ open: true, action: "return" });
  });

  it("submitReasonModal blocks an empty reason", async () => {
    const { result } = await mount();
    act(() => result.current.openReasonModal(pendingOrder, "reject"));
    act(() => result.current.setReasonModal((s) => ({ ...s, value: "   " }) as never));
    act(() => result.current.submitReasonModal());
    expect(result.current.modal).toMatchObject({ title: "原因不可為空" });
  });

  it("submitReasonModal sends a trimmed reason and succeeds", async () => {
    const { result } = await mount();
    act(() => result.current.openReasonModal(pendingOrder, "reject"));
    act(() => result.current.setReasonModal((s) => ({ ...s, value: " 樣品不符 " }) as never));
    await act(async () => {
      result.current.submitReasonModal();
    });
    await waitFor(() =>
      expect(result.current.modal).toMatchObject({ type: "message", title: "簽核操作成功" })
    );
    const actionCall = requestJsonMock.mock.calls.find(([p]) => /actions$/.test(p as string));
    expect(JSON.parse((actionCall?.[1] as { body: string }).body)).toMatchObject({
      action: "reject",
      reason: "樣品不符",
    });
  });

  it("refuses to submit when the order is not pending", async () => {
    const { result } = await mount();
    const closed = { ...pendingOrder, status: "closed" as const };
    act(() => result.current.openReasonModal(closed, "approve"));
    expect(result.current.modal).toMatchObject({ title: "無法執行簽核" });
  });

  it("blocks approval when the actor lacks permission", async () => {
    authValue = { user: adminUser, hasPermission: (p: string) => p !== "orders:approve" };
    const { result } = await mount();
    act(() => result.current.openReasonModal(pendingOrder, "approve"));
    expect(result.current.modal).toMatchObject({ title: "權限不足" });
  });

  it("blocks approval when there is no logged-in actor", async () => {
    authValue = { user: null, hasPermission: () => true };
    routeRequests();
    const { result } = renderHook(() => useApprovePage());
    await waitFor(() => expect(result.current.orders).toHaveLength(1));
    act(() => result.current.openReasonModal(pendingOrder, "approve"));
    expect(result.current.modal).toMatchObject({ title: "尚未登入" });
  });

  it("surfaces a load failure as a message modal", async () => {
    requestJsonMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/orders?status")) return Promise.reject(new Error("載入掛了"));
      return Promise.resolve({ data: { departments: [], labs: [], experiments: [] } });
    });
    const { result } = renderHook(() => useApprovePage());
    await waitFor(() => expect(result.current.modal).toMatchObject({ title: "載入失敗" }));
    expect(result.current.log).toBe("載入掛了");
  });
});
