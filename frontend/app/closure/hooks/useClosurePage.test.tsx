import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("@/services/closures-api", () => ({
  closuresApi: { list: (...a: unknown[]) => listMock(...a) },
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

import { useClosurePage } from "./useClosurePage";

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return QueryWrapper;
}

describe("useClosurePage", () => {
  beforeEach(() => {
    listMock.mockReset();
    hasPermissionMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
  });

  it("loads rows from the closures service and reflects permission", async () => {
    listMock.mockResolvedValue([{ orderNo: "ORD-1" }]);
    const { result } = renderHook(() => useClosurePage(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows).toEqual([{ orderNo: "ORD-1" }]);
    expect(result.current.offline).toBe(false);
    expect(result.current.canOperate).toBe(true);
    expect(hasPermissionMock).toHaveBeenCalledWith("closures:operate");
  });

  it("denies operate when the permission is missing", async () => {
    listMock.mockResolvedValue([]);
    hasPermissionMock.mockReturnValue(false);
    const { result } = renderHook(() => useClosurePage(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.canOperate).toBe(false);
  });

  it("run() sets a success banner when the operation resolves", async () => {
    listMock.mockResolvedValue([]);
    const { result } = renderHook(() => useClosurePage(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.run(() => Promise.resolve(), "已轉待取件");
    });
    expect(result.current.msg).toEqual({ text: "已轉待取件", ok: true });
  });

  it("run() sets an error banner with the backend message when it fails", async () => {
    listMock.mockResolvedValue([]);
    const { result } = renderHook(() => useClosurePage(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.run(
        () => Promise.reject({ response: { data: { error: { message: "尚未驗證" } } } }),
        "ok"
      );
    });
    expect(result.current.msg).toEqual({ text: "尚未驗證", ok: false });
  });

  it("setDetail updates the selected closure detail", async () => {
    listMock.mockResolvedValue([]);
    const { result } = renderHook(() => useClosurePage(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.loading).toBe(false));

    const detail = { orderNo: "ORD-9" } as never;
    act(() => result.current.setDetail(detail));
    expect(result.current.detail).toEqual(detail);
  });
});
