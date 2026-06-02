import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const requestJsonMock = vi.fn();
let authValue: { user: { id: string; name: string } | null };

vi.mock("../lib/api", () => ({
  requestJson: (...a: unknown[]) => requestJsonMock(...a),
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authValue,
}));

import { useOrderTemplatesPage } from "./useOrderTemplatesPage";
import type { Experiment, FormItem, SampleFormGroup } from "../types";

const masterData = {
  labs: [{ id: "lab-1", name: "Lab 1" }],
  experiments: [{ id: "exp-1", name: "E1", labId: "lab-1" }] as Experiment[],
};

function expItem(overrides: Partial<FormItem> = {}): FormItem {
  return {
    sampleId: "SMP-1",
    sampleName: "樣品",
    labId: "lab-1",
    experimentId: "exp-1",
    targetGroup: "G1",
    target: 1,
    check: false,
    ...overrides,
  };
}

async function mount() {
  requestJsonMock.mockResolvedValue({ data: masterData });
  const view = renderHook(() => useOrderTemplatesPage());
  await waitFor(() => expect(view.result.current.masterData.labs).toHaveLength(1));
  return view;
}

describe("useOrderTemplatesPage", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
    window.localStorage.clear();
    authValue = { user: { id: "u1", name: "王小明" } };
  });
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("loads master data on mount and exposes the current user", async () => {
    const { result } = await mount();
    expect(result.current.applicantId).toBe("u1");
    expect(result.current.currentUserName).toBe("王小明");
    expect(result.current.masterData.experiments).toHaveLength(1);
  });

  it("falls back to empty master data when the request fails", async () => {
    requestJsonMock.mockRejectedValue(new Error("down"));
    const { result } = renderHook(() => useOrderTemplatesPage());
    await waitFor(() => expect(result.current.masterData.labs).toEqual([]));
  });

  it("blocks save when the name is empty", async () => {
    const { result } = await mount();
    act(() => result.current.saveTemplate());
    expect(result.current.nameError).toBe("模板名稱不可為空");
    expect(result.current.templates).toHaveLength(0);
  });

  it("blocks save when an experiment item is incomplete", async () => {
    const { result } = await mount();
    act(() => result.current.setTemplateName("我的模板"));
    // default item has empty labId/experimentId => empty flow warning fires first
    act(() => result.current.saveTemplate());
    expect(result.current.message).toContain("尚未加入任何實驗");
    expect(result.current.templates).toHaveLength(0);
  });

  it("creates a new template and persists it to localStorage", async () => {
    const { result } = await mount();
    act(() => {
      result.current.setTemplateName("完整模板");
      result.current.updateDependencyItems(
        { startIndex: 0, endIndex: 0, sampleId: "SMP-1", sampleName: "樣品", items: [] },
        [expItem()]
      );
    });
    act(() => result.current.saveTemplate());

    await waitFor(() => expect(result.current.templates).toHaveLength(1));
    expect(result.current.templates[0].name).toBe("完整模板");
    expect(result.current.selectedTemplateId).toBe(result.current.templates[0].id);
    expect(window.localStorage.getItem("order-management-templates:u1")).toContain("完整模板");
  });

  it("updates an existing template when one is selected", async () => {
    const { result } = await mount();
    act(() => {
      result.current.updateDependencyItems(
        { startIndex: 0, endIndex: 0, sampleId: "SMP-1", sampleName: "樣品", items: [] },
        [expItem()]
      );
      result.current.setTemplateName("原始");
    });
    act(() => result.current.saveTemplate());
    await waitFor(() => expect(result.current.templates).toHaveLength(1));

    act(() => result.current.setTemplateName("更新後"));
    act(() => result.current.saveTemplate());
    await waitFor(() => expect(result.current.templates[0].name).toBe("更新後"));
    expect(result.current.message).toContain("已更新模板");
    expect(result.current.templates).toHaveLength(1);
  });

  it("selects and then deletes a template, resetting the editor", async () => {
    const { result } = await mount();
    act(() => {
      result.current.updateDependencyItems(
        { startIndex: 0, endIndex: 0, sampleId: "SMP-1", sampleName: "樣品", items: [] },
        [expItem()]
      );
      result.current.setTemplateName("待刪除");
    });
    act(() => result.current.saveTemplate());
    await waitFor(() => expect(result.current.templates).toHaveLength(1));
    const id = result.current.templates[0].id;

    act(() => result.current.selectTemplate(result.current.templates[0]));
    expect(result.current.selectedTemplateId).toBe(id);

    act(() => result.current.deleteTemplate(id));
    expect(result.current.templates).toHaveLength(0);
    expect(result.current.selectedTemplateId).toBeNull();
    expect(result.current.message).toContain("已刪除模板：待刪除");
  });

  it("addSample appends an item and removeItem keeps at least one", async () => {
    const { result } = await mount();
    act(() => result.current.addSample());
    expect(result.current.items).toHaveLength(2);
    act(() => result.current.removeItem(1));
    expect(result.current.items).toHaveLength(1);
    // refuses to remove the final item
    act(() => result.current.removeItem(0));
    expect(result.current.items).toHaveLength(1);
  });

  it("updateSampleGroup / updateSampleNameGroup mutate the right range", async () => {
    const { result } = await mount();
    const group: SampleFormGroup = {
      startIndex: 0,
      endIndex: 0,
      sampleId: "SMP-1",
      sampleName: "",
      items: [],
    };
    act(() => result.current.updateSampleGroup(group, "SMP-NEW"));
    expect(result.current.items[0].sampleId).toBe("SMP-NEW");
    act(() => result.current.updateSampleNameGroup(group, "新名稱"));
    expect(result.current.items[0].sampleName).toBe("新名稱");
  });

  it("moveExperiment swaps adjacent items within a sample only", async () => {
    const { result } = await mount();
    act(() => {
      result.current.updateDependencyItems(
        { startIndex: 0, endIndex: 0, sampleId: "SMP-1", sampleName: "樣品", items: [] },
        [expItem({ experimentId: "a" }), expItem({ experimentId: "b" })]
      );
    });
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    act(() => result.current.moveExperiment(0, 1));
    expect(result.current.items.map((i) => i.experimentId)).toEqual(["b", "a"]);
    // out-of-range move is a no-op
    act(() => result.current.moveExperiment(0, -1));
    expect(result.current.items.map((i) => i.experimentId)).toEqual(["b", "a"]);
  });

  it("toggleExperimentForSample adds an experiment item", async () => {
    const { result } = await mount();
    const group = result.current.sampleGroups[0];
    act(() =>
      result.current.toggleExperimentForSample(group, masterData.experiments[0], true)
    );
    expect(result.current.items.some((i) => i.experimentId === "exp-1")).toBe(true);
  });

  it("does nothing on mount when there is no logged-in user", async () => {
    authValue = { user: null };
    requestJsonMock.mockResolvedValue({ data: masterData });
    const { result } = renderHook(() => useOrderTemplatesPage());
    await waitFor(() => expect(result.current.masterData.labs).toHaveLength(1));
    expect(result.current.applicantId).toBe("");
    expect(result.current.templates).toHaveLength(0);
  });
});
