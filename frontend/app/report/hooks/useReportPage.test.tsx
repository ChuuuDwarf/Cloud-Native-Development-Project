import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const reportsListMock = vi.fn();
const listTemplatesMock = vi.fn();
const saveTemplateMock = vi.fn();
const experimentsListMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("@/services/reports-api", () => ({
  reportsApi: {
    list: (...a: unknown[]) => reportsListMock(...a),
    listTemplates: (...a: unknown[]) => listTemplatesMock(...a),
    saveTemplate: (...a: unknown[]) => saveTemplateMock(...a),
  },
}));
vi.mock("@/services/experiments-api", () => ({
  experimentsApi: { list: (...a: unknown[]) => experimentsListMock(...a) },
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

import { useReportPage } from "./useReportPage";

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return QueryWrapper;
}

const reports = [
  { reportId: "R1", wipId: "W1", status: "草稿", title: "草稿報告" },
  { reportId: "R2", wipId: "W2", status: "已發布", title: "正式報告" },
  { reportId: "R3", wipId: "W3", status: "已改版", title: "改版" },
];
const wips = [
  { wipId: "W2", status: "已完成" }, // has a formal report -> excluded from creatable
  { wipId: "W4", status: "待確認" }, // creatable
  { wipId: "W5", status: "進行中" }, // wrong status -> excluded
];

async function mount() {
  reportsListMock.mockResolvedValue(reports);
  experimentsListMock.mockResolvedValue(wips);
  listTemplatesMock.mockResolvedValue([{ id: "t1", name: "T1" }]);
  const view = renderHook(() => useReportPage(), { wrapper: wrapper() });
  await waitFor(() => expect(view.result.current.loading).toBe(false));
  return view;
}

describe("useReportPage", () => {
  beforeEach(() => {
    [
      reportsListMock,
      listTemplatesMock,
      saveTemplateMock,
      experimentsListMock,
      hasPermissionMock,
    ].forEach((m) => m.mockReset());
    hasPermissionMock.mockImplementation((p: string) => p === "reports:operate");
  });
  afterEach(() => vi.restoreAllMocks());

  it("derives creatable / draft / formal lists from the loaded data", async () => {
    const { result } = await mount();
    expect(result.current.creatable.map((w) => w.wipId)).toEqual(["W4"]);
    expect(result.current.draftReports.map((r) => r.reportId)).toEqual(["R1", "R3"]);
    expect(result.current.formalReports.map((r) => r.reportId)).toEqual(["R2"]);
    expect(result.current.templates).toEqual([{ id: "t1", name: "T1" }]);
  });

  it("exposes permission-derived flags", async () => {
    const { result } = await mount();
    expect(result.current.canStaff).toBe(true);
    expect(result.current.isChief).toBe(false);
  });

  it("openCreate / openEdit toggle creating/editing and clear the banner", async () => {
    const { result } = await mount();
    act(() => result.current.openCreate());
    expect(result.current.creating).toBe(true);
    act(() => result.current.openEdit(reports[0] as never));
    expect(result.current.editing).toMatchObject({ reportId: "R1" });
    expect(result.current.msg).toBeNull();
  });

  it("run() sets success banner and resets editing/creating", async () => {
    const { result } = await mount();
    act(() => result.current.setCreating(true));
    await act(async () => {
      await result.current.run(() => Promise.resolve(), "已送審");
    });
    expect(result.current.msg).toEqual({ text: "已送審", ok: true });
    expect(result.current.creating).toBe(false);
    expect(result.current.editing).toBeNull();
  });

  it("run() surfaces backend error message on failure", async () => {
    const { result } = await mount();
    await act(async () => {
      await result.current.run(
        () => Promise.reject({ response: { data: { error: { message: "驗證失敗" } } } }),
        "ok"
      );
    });
    expect(result.current.msg).toEqual({ text: "驗證失敗", ok: false });
  });

  it("saveAsTemplate prompts and saves when a name is given", async () => {
    const { result } = await mount();
    saveTemplateMock.mockResolvedValue(undefined);
    vi.spyOn(window, "prompt").mockReturnValue("我的範本");

    await act(async () => {
      await result.current.saveAsTemplate(reports[1] as never);
    });
    expect(saveTemplateMock).toHaveBeenCalledWith({ name: "我的範本", fromReportId: "R2" });
    expect(result.current.msg).toEqual({ text: "已存成範本", ok: true });
  });

  it("saveAsTemplate aborts when the prompt is cancelled", async () => {
    const { result } = await mount();
    vi.spyOn(window, "prompt").mockReturnValue(null);
    await act(async () => {
      await result.current.saveAsTemplate(reports[1] as never);
    });
    expect(saveTemplateMock).not.toHaveBeenCalled();
  });
});
