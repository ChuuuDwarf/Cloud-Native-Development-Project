import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Experiment, FormItem, SampleFormGroup } from "../types";
import {
  createDefaultItem,
  generateSampleId,
  getDefaultExperimentForLab,
  getNextSampleId,
  getNextSampleIdFromOrders,
  groupItemsBySample,
  toggleExperimentInGroup,
} from "./formItems";

function item(overrides: Partial<FormItem> = {}): FormItem {
  return {
    sampleId: "SMP-1",
    sampleName: "",
    labId: "",
    experimentId: "",
    targetGroup: "G1",
    target: 1,
    check: false,
    ...overrides,
  };
}

const masterData = {
  labs: [{ id: "lab-1", name: "Lab 1" }],
  experiments: [
    { id: "exp-1", name: "E1", labId: "lab-1" },
    { id: "exp-2", name: "E2", labId: "lab-2" },
  ] as Experiment[],
};

describe("orders/lib/formItems", () => {
  describe("groupItemsBySample", () => {
    it("groups consecutive items sharing a sampleId", () => {
      const items = [
        item({ sampleId: "A", sampleName: "Alpha" }),
        item({ sampleId: "A" }),
        item({ sampleId: "B", sampleName: "Beta" }),
      ];
      const groups = groupItemsBySample(items);
      expect(groups).toHaveLength(2);
      expect(groups[0]).toMatchObject({ sampleId: "A", startIndex: 0, endIndex: 1 });
      expect(groups[0].items).toHaveLength(2);
      expect(groups[1]).toMatchObject({ sampleId: "B", startIndex: 2, endIndex: 2 });
    });

    it("starts a new group when sampleId changes then repeats", () => {
      const items = [item({ sampleId: "A" }), item({ sampleId: "B" }), item({ sampleId: "A" })];
      const groups = groupItemsBySample(items);
      expect(groups.map((g) => g.sampleId)).toEqual(["A", "B", "A"]);
    });

    it("defaults missing sampleName to empty string", () => {
      const groups = groupItemsBySample([item({ sampleId: "A", sampleName: undefined as never })]);
      expect(groups[0].sampleName).toBe("");
    });
  });

  describe("getDefaultExperimentForLab", () => {
    it("returns the first experiment matching the lab", () => {
      expect(getDefaultExperimentForLab(masterData, "lab-1")).toBe("exp-1");
    });

    it("returns empty string when no experiment matches", () => {
      expect(getDefaultExperimentForLab(masterData, "lab-9")).toBe("");
    });
  });

  describe("generateSampleId", () => {
    it("zero-pads the sequence and uses the provided date text", () => {
      expect(generateSampleId(5, "20260101")).toBe("SMP-20260101-005");
      expect(generateSampleId(123, "20260101")).toBe("SMP-20260101-123");
    });
  });

  describe("getNextSampleId / getNextSampleIdFromOrders", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2026-03-09T10:00:00"));
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it("increments from the max same-date sequence", () => {
      const items = [
        item({ sampleId: "SMP-20260309-001" }),
        item({ sampleId: "SMP-20260309-004" }),
        // different date is ignored
        item({ sampleId: "SMP-20251231-099" }),
      ];
      expect(getNextSampleId(items)).toBe("SMP-20260309-005");
    });

    it("starts at 001 when no same-date ids exist", () => {
      expect(getNextSampleId([item({ sampleId: "" })])).toBe("SMP-20260309-001");
    });

    it("derives next id across nested order items", () => {
      const orders = [
        { items: [{ sampleId: "SMP-20260309-002" }, { sampleId: "SMP-20260309-007" }] },
        { items: [{ sampleId: "SMP-20260309-003" }] },
        { items: undefined },
      ];
      expect(getNextSampleIdFromOrders(orders)).toBe("SMP-20260309-008");
    });
  });

  describe("createDefaultItem", () => {
    it("creates a blank item with a default sample id", () => {
      const created = createDefaultItem(masterData);
      expect(created).toMatchObject({
        sampleName: "",
        labId: "",
        experimentId: "",
        targetGroup: "G1",
        target: 1,
        check: false,
      });
      expect(created.sampleId).toMatch(/^SMP-\d{8}-001$/);
    });

    it("honors an explicit sampleId", () => {
      expect(createDefaultItem(masterData, "SMP-X").sampleId).toBe("SMP-X");
    });
  });

  describe("toggleExperimentInGroup", () => {
    const group: SampleFormGroup = {
      sampleId: "A",
      sampleName: "Alpha",
      startIndex: 0,
      endIndex: 0,
      items: [{ item: item({ sampleId: "A" }), index: 0 }],
    };
    const exp: Experiment = { id: "exp-2", name: "E2", labId: "lab-2" };

    it("adds a new item for the experiment when checked", () => {
      const current = [item({ sampleId: "A" })];
      const next = toggleExperimentInGroup(current, group, exp, true);
      expect(next).toHaveLength(2);
      expect(next[1]).toMatchObject({ sampleId: "A", labId: "lab-2", experimentId: "exp-2" });
    });

    it("does not duplicate an experiment already present", () => {
      const current = [item({ sampleId: "A", experimentId: "exp-2" })];
      const next = toggleExperimentInGroup(current, group, exp, true);
      expect(next).toBe(current);
    });

    it("removes the experiment item when unchecked", () => {
      const current = [
        item({ sampleId: "A", experimentId: "exp-1" }),
        item({ sampleId: "A", experimentId: "exp-2" }),
      ];
      const grp: SampleFormGroup = { ...group, endIndex: 1 };
      const next = toggleExperimentInGroup(current, grp, exp, false);
      expect(next).toHaveLength(1);
      expect(next[0].experimentId).toBe("exp-1");
    });

    it("refuses to remove the last remaining item", () => {
      const current = [item({ sampleId: "A", experimentId: "exp-2" })];
      const next = toggleExperimentInGroup(current, group, exp, false);
      expect(next).toBe(current);
    });

    it("is a no-op when unchecking a missing experiment", () => {
      const current = [
        item({ sampleId: "A", experimentId: "exp-1" }),
        item({ sampleId: "A", experimentId: "exp-9" }),
      ];
      const grp: SampleFormGroup = { ...group, endIndex: 1 };
      const next = toggleExperimentInGroup(current, grp, exp, false);
      expect(next).toBe(current);
    });
  });
});
