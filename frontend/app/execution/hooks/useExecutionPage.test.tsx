import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const experimentsListMock = vi.fn();
const machinesListMock = vi.fn();
const recipesListMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("@/services/experiments-api", () => ({
  experimentsApi: { list: (...a: unknown[]) => experimentsListMock(...a) },
}));
vi.mock("@/services/machines-api", () => ({
  machinesApi: { list: (...a: unknown[]) => machinesListMock(...a) },
}));
vi.mock("@/services/recipes-api", () => ({
  recipesApi: { list: (...a: unknown[]) => recipesListMock(...a) },
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

import { useExecutionPage } from "./useExecutionPage";

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return QueryWrapper;
}

const wips = [
  { wipId: "W1", status: "待上機" },
  { wipId: "W2", status: "執行中" },
  { wipId: "W3", status: "執行中" },
  { wipId: "W4", status: "已完成" },
];

async function mount() {
  experimentsListMock.mockResolvedValue(wips);
  machinesListMock.mockResolvedValue([{ id: "m1" }]);
  recipesListMock.mockResolvedValue([{ id: "r1" }]);
  const view = renderHook(() => useExecutionPage(), { wrapper: wrapper() });
  await waitFor(() => expect(view.result.current.loading).toBe(false));
  return view;
}

describe("useExecutionPage", () => {
  beforeEach(() => {
    [experimentsListMock, machinesListMock, recipesListMock, hasPermissionMock].forEach((m) =>
      m.mockReset()
    );
    hasPermissionMock.mockImplementation((p: string) => p === "experiments:operate");
  });
  afterEach(() => vi.restoreAllMocks());

  it("computes KPI counts per status", async () => {
    const { result } = await mount();
    expect(result.current.kpi).toEqual({
      checkin: 1,
      running: 2,
      out: 0,
      confirm: 0,
      done: 1,
    });
  });

  it("exposes permission flags and loaded machines/recipes", async () => {
    const { result } = await mount();
    expect(result.current.canOperate).toBe(true);
    expect(result.current.isChief).toBe(false);
    expect(result.current.machines).toEqual([{ id: "m1" }]);
    expect(result.current.recipes).toEqual([{ id: "r1" }]);
  });

  it("open sets the target + modal kind and clears the banner", async () => {
    const { result } = await mount();
    act(() => result.current.open("checkin", wips[0] as never));
    expect(result.current.modal).toBe("checkin");
    expect(result.current.target).toMatchObject({ wipId: "W1" });
    expect(result.current.msg).toBeNull();
  });

  it("run resolves with success banner and closes the modal", async () => {
    const { result } = await mount();
    act(() => result.current.open("checkin", wips[0] as never));
    await act(async () => {
      await result.current.run(() => Promise.resolve(), "已上機");
    });
    expect(result.current.msg).toEqual({ text: "已上機", ok: true });
    expect(result.current.modal).toBeNull();
  });

  it("run shows the backend error message on failure", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.run(
        () => Promise.reject({ response: { data: { error: { message: "機台忙碌" } } } }),
        "ok"
      );
    });
    expect(result.current.msg).toEqual({ text: "機台忙碌", ok: false });
  });

  it("closeModal and flashError behave as expected", async () => {
    const { result } = await mount();
    act(() => result.current.open("checkin", wips[0] as never));
    act(() => result.current.closeModal());
    expect(result.current.modal).toBeNull();
    act(() => result.current.flashError("出錯了"));
    expect(result.current.msg).toEqual({ text: "出錯了", ok: false });
  });
});
