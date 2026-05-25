import { describe, expect, it } from "vitest";

import type { CurrentUser, Sample, Wip } from "../types";
import {
  createEmptyWipForm,
  formatRequestedExperiments,
  getCurrentLab,
  getRequestedExperiments,
  makeAutoFormsForSample,
  parseExperimentsFromSummary,
  shouldOpenCreateWipByDefault,
} from "./wipForm";

const baseSample: Sample = {
  id: "sample-1",
  sample_no: "SMP-2026-0001",
  order_no: "ORD-2026-0001",
  sample_name: "測試樣品",
  experiment_item: "Lab A:SEM 觀察、Lab B:光學量測、Lab A:EDS 分析",
  applicant_name: "王小明",
  applicant_department: "廠區一課",
  status: "received",
  current_location: "Lab A 實驗暫存區",
  storage_location_id: null,
  received_at: null,
  received_by: null,
  picked_up_at: null,
  picked_up_by: null,
  note: "使用者備註不應被解析成實驗需求",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const baseWip: Wip = {
  id: "wip-1",
  wip_no: "WIP-2026-0001-A-01",
  sample_id: "sample-1",
  order_no: "ORD-2026-0001",
  lab_name: "Lab A",
  experiment_item: "SEM 觀察",
  priority: "normal",
  status: "created",
  progress: 0,
  current_location: "Lab A 實驗暫存區",
  scheduled_at: null,
  dispatched_at: null,
  started_at: null,
  completed_at: null,
  terminated_at: null,
  note: null,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("wipForm 功能測試", () => {
  it("建立空白 WIP 表單時會帶入目前 Lab 與預設 priority", () => {
    expect(createEmptyWipForm("Lab A")).toEqual({
      lab_name: "Lab A",
      experiment_item: "",
      priority: "normal",
      note: "",
      auto_generated: false,
    });
  });

  it("目前 Lab 優先使用 lab_name，沒有 lab_name 時才使用 department", () => {
    const userWithLab: CurrentUser = {
      id: "u1",
      name: "張志明",
      role: "lab_engineer",
      department: "Lab B",
      lab_name: "Lab A",
    };
    const userWithoutLab: CurrentUser = {
      id: "u2",
      name: "李小華",
      role: "lab_engineer",
      department: "Lab B",
      lab_name: null,
    };

    expect(getCurrentLab(userWithLab)).toBe("Lab A");
    expect(getCurrentLab(userWithoutLab)).toBe("Lab B");
  });

  it("只從 experiment_item 解析實驗需求，支援多 Lab 與冒號後面的內容", () => {
    expect(parseExperimentsFromSummary("Lab A:SEM:高倍率、Lab B:光學量測")).toEqual([
      { lab_name: "Lab A", experiment_item: "SEM:高倍率" },
      { lab_name: "Lab B", experiment_item: "光學量測" },
    ]);

    expect(getRequestedExperiments(baseSample)).toHaveLength(3);
    expect(formatRequestedExperiments(baseSample)).toBe(
      "Lab A:SEM 觀察、Lab B:光學量測、Lab A:EDS 分析"
    );
  });

  it("A -> B -> A 時不會跨過 B 自動產生最後一個 A", () => {
    const forms = makeAutoFormsForSample(baseSample, "Lab A", [baseWip]);

    expect(forms).toEqual([createEmptyWipForm("Lab A")]);
  });

  it("A -> A -> B 時可以一次自動產生兩個連續 A WIP 表單", () => {
    const aabSample = {
      ...baseSample,
      experiment_item: "Lab A:SEM 觀察、Lab A:EDS 分析、Lab B:光學量測",
    };

    const forms = makeAutoFormsForSample(aabSample, "Lab A", []);

    expect(forms).toEqual([
      {
        lab_name: "Lab A",
        experiment_item: "SEM 觀察",
        priority: "normal",
        note: "由委託單實驗需求自動帶入",
        auto_generated: true,
      },
      {
        lab_name: "Lab A",
        experiment_item: "EDS 分析",
        priority: "normal",
        note: "由委託單實驗需求自動帶入",
        auto_generated: true,
      },
    ]);
  });

  it("同 Lab 實驗都已建立 WIP 時回到空白表單，避免重複建單", () => {
    const forms = makeAutoFormsForSample(baseSample, "Lab A", [
      baseWip,
      { ...baseWip, id: "wip-2", wip_no: "WIP-2026-0001-A-02", experiment_item: "EDS 分析" },
    ]);

    expect(forms).toEqual([createEmptyWipForm("Lab A")]);
  });

  it("已分貨樣品預設收合建立 WIP 區塊，未分貨或未選樣品則展開", () => {
    expect(shouldOpenCreateWipByDefault(null)).toBe(true);
    expect(shouldOpenCreateWipByDefault({ ...baseSample, status: "received" })).toBe(true);
    expect(shouldOpenCreateWipByDefault({ ...baseSample, status: "split" })).toBe(false);
  });
});
