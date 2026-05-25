import { describe, expect, it, vi } from "vitest";

import type { CurrentUser, Sample, Transfer } from "../types";
import {
  filterSamplesByView,
  formatDateTime,
  formatStatusChange,
  getDisplaySampleLocation,
  getDisplaySampleStatus,
  getUserLab,
  isActiveSampleStatus,
  isSampleInCurrentLab,
  isSampleVisibleForUser,
  shouldMaskSampleForLab,
} from "./sampleDisplay";

const labAUser: CurrentUser = {
  id: "u1",
  name: "張志明",
  role: "lab_engineer",
  department: "Lab A",
  lab_name: "Lab A",
};

const labSupervisor: CurrentUser = {
  id: "u2",
  name: "李主管",
  role: "lab_supervisor",
  department: "Lab A",
  lab_name: "Lab A",
};

const labUserWithoutLabName: CurrentUser = {
  id: "u3",
  name: "林人員",
  role: "lab_engineer",
  department: "Lab A",
  lab_name: null,
};

const labBUser: CurrentUser = {
  id: "u4",
  name: "陳人員",
  role: "lab_engineer",
  department: "Lab B",
  lab_name: "Lab B",
};

const factoryUser: CurrentUser = {
  id: "f1",
  name: "王小明",
  role: "plant_user",
  department: "廠區一課",
};

const systemAdmin: CurrentUser = {
  id: "admin-1",
  name: "系統管理者",
  role: "system_admin",
  department: "IT",
};

const unknownUser: CurrentUser = {
  id: "guest-1",
  name: "訪客",
  role: "guest",
  department: "外部",
};

const sample: Sample = {
  id: "sample-1",
  sample_no: "SMP-2026-0001",
  order_no: "ORD-2026-0001",
  sample_name: "測試樣品",
  experiment_item: "Lab A:SEM、Lab B:光學量測",
  applicant_name: "王小明",
  applicant_department: "廠區一課",
  status: "split",
  current_location: "Lab A 實驗暫存區",
  storage_location_id: null,
  received_at: null,
  received_by: null,
  picked_up_at: null,
  picked_up_by: null,
  note: null,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const transferBase: Transfer = {
  id: "trf-1",
  transfer_no: "TRF-2026-0001",
  target_type: "sample",
  target_id: "sample-1",
  order_no: "ORD-2026-0001",
  sample_no: "SMP-2026-0001",
  wip_no: null,
  from_lab: "Lab A",
  to_lab: "Lab B",
  handed_by: "張志明",
  received_by: null,
  status: "transferring",
  transferred_at: null,
  received_at: null,
  note: null,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const transferredOutSample: Sample = {
  ...sample,
  current_location: "Lab B 實驗暫存區",
};

const makeSample = (overrides: Partial<Sample>): Sample => ({
  ...sample,
  ...overrides,
});

describe("sampleDisplay 功能測試", () => {
  it("判斷目前使用者 Lab，lab_name 為空時改用 department", () => {
    expect(getUserLab(labAUser)).toBe("Lab A");
    expect(getUserLab(labUserWithoutLabName)).toBe("Lab A");
  });

  it("判斷樣品是否位於目前 Lab，處理 null sample、admin、非 Lab 角色與空位置", () => {
    expect(isSampleInCurrentLab(sample, labAUser)).toBe(true);
    expect(isSampleInCurrentLab(null, labAUser)).toBe(false);
    expect(isSampleInCurrentLab(sample, systemAdmin)).toBe(false);
    expect(isSampleInCurrentLab(sample, factoryUser)).toBe(false);
    expect(isSampleInCurrentLab(makeSample({ current_location: null }), labAUser)).toBe(false);
    expect(
      isSampleInCurrentLab(makeSample({ current_location: "Lab B 實驗暫存區" }), labAUser)
    ).toBe(false);
  });

  it("判斷 active 樣品狀態，排除已完成、異常與取消狀態", () => {
    expect(isActiveSampleStatus("pending_receive")).toBe(true);
    expect(isActiveSampleStatus("received")).toBe(true);
    expect(isActiveSampleStatus("split")).toBe(true);
    expect(isActiveSampleStatus("transferring")).toBe(true);
    expect(isActiveSampleStatus("in_storage")).toBe(true);

    expect(isActiveSampleStatus("outbound")).toBe(false);
    expect(isActiveSampleStatus("picked_up")).toBe(false);
    expect(isActiveSampleStatus("lost")).toBe(false);
    expect(isActiveSampleStatus("damaged")).toBe(false);
    expect(isActiveSampleStatus("cancelled")).toBe(false);
  });

  it("判斷哪些角色需要遮罩已離開本 Lab 的樣品", () => {
    expect(shouldMaskSampleForLab(transferredOutSample, labAUser)).toBe(true);
    expect(shouldMaskSampleForLab(transferredOutSample, labSupervisor)).toBe(true);
    expect(shouldMaskSampleForLab(transferredOutSample, factoryUser)).toBe(false);
    expect(shouldMaskSampleForLab(transferredOutSample, systemAdmin)).toBe(false);
    expect(shouldMaskSampleForLab(transferredOutSample, unknownUser)).toBe(false);
  });

  it("Lab 使用者看到已離開本 Lab 的樣品時，依交接狀態顯示遮罩狀態", () => {
    expect(
      getDisplaySampleStatus(transferredOutSample, labAUser, { ...transferBase, status: "pending" })
    ).toBe("transfer_pending");

    expect(
      getDisplaySampleStatus(transferredOutSample, labAUser, {
        ...transferBase,
        status: "transferring",
      })
    ).toBe("transferred_waiting_receive");

    expect(
      getDisplaySampleStatus(transferredOutSample, labAUser, {
        ...transferBase,
        status: "received",
      })
    ).toBe("transferred_received");

    expect(
      getDisplaySampleStatus(transferredOutSample, labAUser, {
        ...transferBase,
        status: "cancelled",
      })
    ).toBe("cancelled");
  });

  it("Lab 使用者看到已離開本 Lab 的樣品時，特殊樣品狀態仍顯示異常或取消", () => {
    expect(
      getDisplaySampleStatus(
        makeSample({ status: "cancelled", current_location: "Lab B" }),
        labAUser
      )
    ).toBe("cancelled");

    expect(
      getDisplaySampleStatus(makeSample({ status: "lost", current_location: "Lab B" }), labAUser)
    ).toBe("lost");

    expect(
      getDisplaySampleStatus(makeSample({ status: "damaged", current_location: "Lab B" }), labAUser)
    ).toBe("damaged");

    expect(getDisplaySampleStatus(transferredOutSample, labAUser)).toBe("transferred_out");
  });

  it("Lab 使用者看到已離開本 Lab 的樣品時，依交接狀態顯示遮罩位置", () => {
    expect(
      getDisplaySampleLocation(transferredOutSample, labAUser, {
        ...transferBase,
        status: "pending",
      })
    ).toBe("本實驗室交接待送區");

    expect(
      getDisplaySampleLocation(transferredOutSample, labAUser, {
        ...transferBase,
        status: "transferring",
      })
    ).toBe("已送出，等待接收實驗室（Lab B）收樣");

    expect(
      getDisplaySampleLocation(transferredOutSample, labAUser, {
        ...transferBase,
        status: "received",
      })
    ).toBe("已由接收實驗室（Lab B）收樣");

    expect(
      getDisplaySampleLocation(transferredOutSample, labAUser, {
        ...transferBase,
        status: "cancelled",
      })
    ).toBe("交接已取消");
  });

  it("遮罩位置在沒有 to_lab 或特殊狀態時仍有可讀 fallback", () => {
    const transferWithoutReceiver = { ...transferBase, to_lab: null, status: "transferring" };

    expect(getDisplaySampleLocation(transferredOutSample, labAUser, transferWithoutReceiver)).toBe(
      "已送出，等待接收實驗室收樣"
    );

    expect(
      getDisplaySampleLocation(
        makeSample({ status: "cancelled", current_location: "Lab B" }),
        labAUser
      )
    ).toBe("流程已取消");

    expect(
      getDisplaySampleLocation(makeSample({ status: "lost", current_location: "Lab B" }), labAUser)
    ).toBe("樣品異常：遺失");

    expect(
      getDisplaySampleLocation(
        makeSample({ status: "damaged", current_location: "Lab B" }),
        labAUser
      )
    ).toBe("樣品異常：破損");

    expect(getDisplaySampleLocation(transferredOutSample, labAUser)).toBe("已離開本實驗室");
  });

  it("位於目前 Lab 的樣品不遮罩，直接顯示真實狀態與位置，空位置顯示 -", () => {
    expect(shouldMaskSampleForLab(sample, labAUser)).toBe(false);
    expect(getDisplaySampleStatus(sample, labAUser, transferBase)).toBe("split");
    expect(getDisplaySampleLocation(sample, labAUser, transferBase)).toBe("Lab A 實驗暫存區");
    expect(getDisplaySampleLocation(makeSample({ current_location: null }), systemAdmin)).toBe("-");
  });

  it("依角色判斷樣品是否可見", () => {
    expect(isSampleVisibleForUser(sample, systemAdmin)).toBe(true);
    expect(isSampleVisibleForUser(sample, labAUser)).toBe(true);
    expect(isSampleVisibleForUser(sample, labSupervisor)).toBe(true);
    expect(isSampleVisibleForUser(sample, factoryUser)).toBe(true);
    expect(isSampleVisibleForUser(makeSample({ applicant_name: "陳大華" }), factoryUser)).toBe(
      false
    );
    expect(isSampleVisibleForUser(sample, unknownUser)).toBe(false);
  });

  it("廠區使用者只能看到自己的樣品，並可篩選 active、待取件與已取回", () => {
    const samples = [
      sample,
      makeSample({ id: "sample-2", applicant_name: "陳大華", status: "outbound" }),
      makeSample({ id: "sample-3", status: "outbound" }),
      makeSample({ id: "sample-4", status: "picked_up" }),
    ];

    expect(filterSamplesByView(samples, factoryUser, "all").map((item) => item.id)).toEqual([
      "sample-1",
      "sample-3",
      "sample-4",
    ]);

    expect(filterSamplesByView(samples, factoryUser, "active").map((item) => item.id)).toEqual([
      "sample-1",
    ]);
    expect(filterSamplesByView(samples, factoryUser, "current").map((item) => item.id)).toEqual([
      "sample-1",
      "sample-3",
      "sample-4",
    ]);
    expect(filterSamplesByView(samples, factoryUser, "outbound").map((item) => item.id)).toEqual([
      "sample-3",
    ]);
    expect(filterSamplesByView(samples, factoryUser, "picked_up").map((item) => item.id)).toEqual([
      "sample-4",
    ]);
  });

  it("Lab 使用者可依目前 Lab、active、待取件、已取回篩選樣品", () => {
    const samples = [
      sample,
      makeSample({ id: "sample-2", current_location: "Lab B 實驗暫存區", status: "received" }),
      makeSample({ id: "sample-3", current_location: "Lab A 出庫待取區", status: "outbound" }),
      makeSample({ id: "sample-4", current_location: "Lab B 出庫待取區", status: "outbound" }),
      makeSample({ id: "sample-5", current_location: "Lab A", status: "picked_up" }),
    ];

    expect(filterSamplesByView(samples, labAUser, "current").map((item) => item.id)).toEqual([
      "sample-1",
      "sample-3",
      "sample-5",
    ]);

    expect(filterSamplesByView(samples, labAUser, "active").map((item) => item.id)).toEqual([
      "sample-1",
      "sample-3",
      "sample-5",
    ]);

    expect(filterSamplesByView(samples, labAUser, "outbound").map((item) => item.id)).toEqual([
      "sample-3",
    ]);
    expect(filterSamplesByView(samples, labAUser, "picked_up").map((item) => item.id)).toEqual([
      "sample-5",
    ]);
    expect(filterSamplesByView(samples, labBUser, "outbound").map((item) => item.id)).toEqual([
      "sample-4",
    ]);
    expect(filterSamplesByView(samples, labAUser, "all")).toHaveLength(5);
  });

  it("未知角色只回傳原本可見的資料集合", () => {
    expect(filterSamplesByView([sample], unknownUser, "all")).toEqual([]);
  });

  it("格式化日期時間，空值顯示 -，toLocaleString 失敗時回傳原字串", () => {
    expect(formatDateTime(null)).toBe("-");

    const spy = vi.spyOn(Date.prototype, "toLocaleString").mockImplementation(() => {
      throw new Error("format error");
    });

    expect(formatDateTime("not-a-date")).toBe("not-a-date");

    spy.mockRestore();
  });

  it("狀態異動文字使用中文對照，未知狀態保留原值，缺任一狀態時顯示無", () => {
    expect(formatStatusChange("received", "split")).toBe("已收樣 → 已分貨");
    expect(formatStatusChange(null, null)).toBe("狀態未變更");
    expect(formatStatusChange("unknown", "split")).toBe("unknown → 已分貨");
    expect(formatStatusChange(null, "received")).toBe("無 → 已收樣");
    expect(formatStatusChange("received", null)).toBe("已收樣 → 無");
  });

  it("樣品已被廠區取回時，送出 Lab 仍停留在交接歷程視角", () => {
    const pickedUpSample = makeSample({
      status: "picked_up",
      current_location: "已由使用者取回",
      picked_up_by: "王建國",
      picked_up_at: "2026-05-23T10:00:00",
    });

    const receivedTransfer = {
      ...transferBase,
      status: "received",
      from_lab: "Lab A",
      to_lab: "Lab B",
    } as Transfer;

    expect(getDisplaySampleStatus(pickedUpSample, labBUser, receivedTransfer)).toBe("picked_up");
    expect(getDisplaySampleLocation(pickedUpSample, labBUser, receivedTransfer)).toBe(
      "已由使用者取回"
    );

    expect(getDisplaySampleStatus(pickedUpSample, labAUser, receivedTransfer)).toBe(
      "transferred_received"
    );
    expect(getDisplaySampleLocation(pickedUpSample, labAUser, receivedTransfer)).toBe(
      "已由接收實驗室（Lab B）收樣"
    );
  });
});
