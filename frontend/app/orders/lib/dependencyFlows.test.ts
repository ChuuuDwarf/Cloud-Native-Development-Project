import { describe, expect, it } from "vitest";

import type { FormItem } from "../types";
import {
  buildDependencyFlowsFromItems,
  createNextTargetGroup,
  flattenDependencyFlowsToItems,
  getEmptyDependencyFlowNames,
  isExperimentItem,
  moveItemInFlow,
  moveItemToFlow,
  normalizeDependencyItemsForSubmit,
  normalizeTargetsInFlow,
  removeItemFromFlow,
  type DependencyFlow,
  type IndexedDependencyItem,
} from "./dependencyFlows";

function item(overrides: Partial<FormItem> = {}): FormItem {
  return {
    sampleId: "S1",
    sampleName: "Sample 1",
    labId: "lab-1",
    experimentId: "exp-1",
    targetGroup: "G1",
    target: 1,
    check: false,
    ...overrides,
  };
}

function indexed(items: FormItem[]): IndexedDependencyItem[] {
  return items.map((it, index) => ({ item: it, index }));
}

describe("orders/lib/dependencyFlows", () => {
  describe("isExperimentItem", () => {
    it("requires both labId and experimentId (trimmed)", () => {
      expect(isExperimentItem({ labId: "lab-1", experimentId: "exp-1" })).toBe(true);
      expect(isExperimentItem({ labId: " ", experimentId: "exp-1" })).toBe(false);
      expect(isExperimentItem({ labId: "lab-1", experimentId: "  " })).toBe(false);
      expect(isExperimentItem({ labId: "", experimentId: "" })).toBe(false);
    });
  });

  describe("createNextTargetGroup", () => {
    it("returns G1 for empty input", () => {
      expect(createNextTargetGroup([])).toBe("G1");
    });

    it("computes max+1 from FormItem and string groups", () => {
      expect(createNextTargetGroup(["G2", "G5"])).toBe("G6");
      expect(createNextTargetGroup([item({ targetGroup: "G3" }), "G1"])).toBe("G4");
    });

    it("treats unparseable groups as 0", () => {
      expect(createNextTargetGroup(["weird", "G2"])).toBe("G3");
      expect(createNextTargetGroup(["weird"])).toBe("G1");
    });
  });

  describe("buildDependencyFlowsFromItems", () => {
    it("groups experiment items by targetGroup and renumbers targets", () => {
      const items = indexed([
        item({ targetGroup: "G1", experimentId: "exp-a" }),
        item({ targetGroup: "G1", experimentId: "exp-b" }),
        item({ targetGroup: "G2", experimentId: "exp-c" }),
      ]);
      const { flows } = buildDependencyFlowsFromItems(items);
      expect(flows.map((f) => f.id)).toEqual(["G1", "G2"]);
      expect(flows[0].name).toBe("相依流程 1");
      expect(flows[0].items.map((e) => e.item.target)).toEqual([1, 2]);
      expect(flows[1].items[0].item.target).toBe(1);
    });

    it("keeps an empty group entry for non-experiment items", () => {
      const items = indexed([item({ targetGroup: "G1", labId: "", experimentId: "" })]);
      const { flows } = buildDependencyFlowsFromItems(items);
      expect(flows).toHaveLength(1);
      expect(flows[0].items).toHaveLength(0);
      // sample metadata is still captured
      expect(flows[0].sampleId).toBe("S1");
    });

    it("includes explicit flow ids even when empty, sorted by group number", () => {
      const items = indexed([item({ targetGroup: "G2" })]);
      const { flows } = buildDependencyFlowsFromItems(items, ["G5", "G1"]);
      expect(flows.map((f) => f.id)).toEqual(["G1", "G2", "G5"]);
    });

    it("derives a default group from index when targetGroup missing", () => {
      const items = indexed([item({ targetGroup: "" })]);
      const { flows } = buildDependencyFlowsFromItems(items);
      expect(flows[0].id).toBe("G1");
    });
  });

  describe("normalizeTargetsInFlow", () => {
    it("renumbers item targets 1..n and clears check", () => {
      const flow: DependencyFlow = {
        id: "G1",
        name: "x",
        items: indexed([
          item({ target: 9, check: true }),
          item({ experimentId: "exp-b", target: 4, check: true }),
        ]),
      };
      const next = normalizeTargetsInFlow(flow);
      expect(next.items.map((e) => e.item.target)).toEqual([1, 2]);
      expect(next.items.every((e) => e.item.check === false)).toBe(true);
      expect(next.items.every((e) => e.item.targetGroup === "G1")).toBe(true);
    });
  });

  describe("flattenDependencyFlowsToItems", () => {
    it("emits experiment items from each flow", () => {
      const flows: DependencyFlow[] = [
        {
          id: "G1",
          name: "x",
          items: indexed([item({ experimentId: "exp-a" }), item({ experimentId: "exp-b" })]),
        },
      ];
      const out = flattenDependencyFlowsToItems(flows);
      expect(out).toHaveLength(2);
      expect(out.map((i) => i.target)).toEqual([1, 2]);
    });

    it("emits a placeholder item for an empty flow", () => {
      const flows: DependencyFlow[] = [
        { id: "G3", name: "x", sampleId: "S9", sampleName: "Nine", items: [] },
      ];
      const out = flattenDependencyFlowsToItems(flows);
      expect(out).toEqual([
        {
          sampleId: "S9",
          sampleName: "Nine",
          labId: "",
          experimentId: "",
          targetGroup: "G3",
          target: 1,
          check: false,
        },
      ]);
    });

    it("appends independent experiment items with fresh groups", () => {
      const flows: DependencyFlow[] = [
        { id: "G1", name: "x", items: indexed([item({ experimentId: "exp-a" })]) },
      ];
      const independent = indexed([item({ experimentId: "exp-z", labId: "lab-9" })]);
      const out = flattenDependencyFlowsToItems(flows, independent);
      expect(out).toHaveLength(2);
      expect(out[1].experimentId).toBe("exp-z");
      // independent gets a group beyond existing G1
      expect(out[1].targetGroup).not.toBe("G1");
    });

    it("skips independent items that are not experiment items", () => {
      const independent = indexed([item({ labId: "", experimentId: "" })]);
      expect(flattenDependencyFlowsToItems([], independent)).toEqual([]);
    });
  });

  describe("moveItemInFlow", () => {
    const flows: DependencyFlow[] = [
      {
        id: "G1",
        name: "x",
        items: indexed([item({ experimentId: "a" }), item({ experimentId: "b" })]),
      },
    ];

    it("swaps adjacent items and renumbers", () => {
      const next = moveItemInFlow(flows, "G1", 0, 1);
      expect(next[0].items.map((e) => e.item.experimentId)).toEqual(["b", "a"]);
      expect(next[0].items.map((e) => e.item.target)).toEqual([1, 2]);
    });

    it("is a no-op at the boundaries (flow object preserved)", () => {
      // .map() returns a fresh array, but the unchanged flow keeps its identity.
      expect(moveItemInFlow(flows, "G1", 0, -1)[0]).toBe(flows[0]);
      expect(moveItemInFlow(flows, "G1", 1, 1)[0]).toBe(flows[0]);
    });

    it("leaves other flows untouched", () => {
      const next = moveItemInFlow(flows, "G9", 0, 1);
      expect(next[0]).toBe(flows[0]);
    });
  });

  describe("moveItemToFlow", () => {
    const state = {
      flows: [
        { id: "G1", name: "x", items: indexed([item({ experimentId: "a" })]) },
        { id: "G2", name: "y", items: indexed([item({ experimentId: "b" })]) },
      ] as DependencyFlow[],
      independentItems: [],
    };

    it("moves an item from source to target flow", () => {
      const next = moveItemToFlow(state, "G1", 0, "G2");
      expect(next.flows[0].items).toHaveLength(0);
      expect(next.flows[1].items.map((e) => e.item.experimentId)).toEqual(["b", "a"]);
    });

    it("returns the same state when source equals target", () => {
      expect(moveItemToFlow(state, "G1", 0, "G1")).toBe(state);
    });

    it("returns the same state when source/target/item invalid", () => {
      expect(moveItemToFlow(state, "G9", 0, "G2")).toBe(state);
      expect(moveItemToFlow(state, "G1", 5, "G2")).toBe(state);
      expect(moveItemToFlow(state, "G1", 0, "G9")).toBe(state);
    });
  });

  describe("removeItemFromFlow", () => {
    const state = {
      flows: [
        {
          id: "G1",
          name: "x",
          items: indexed([item({ experimentId: "a" }), item({ experimentId: "b" })]),
        },
      ] as DependencyFlow[],
      independentItems: [],
    };

    it("pulls the removed item into a new trailing flow", () => {
      const next = removeItemFromFlow(state, "G1", 0);
      expect(next.flows[0].items.map((e) => e.item.experimentId)).toEqual(["b"]);
      expect(next.flows[1].id).toBe("G2");
      expect(next.flows[1].items[0].item.experimentId).toBe("a");
    });

    it("returns the same state for an invalid index", () => {
      expect(removeItemFromFlow(state, "G1", 9)).toBe(state);
      expect(removeItemFromFlow(state, "G9", 0)).toBe(state);
    });
  });

  describe("normalizeDependencyItemsForSubmit", () => {
    it("renumbers groups sequentially across samples", () => {
      const items = [
        item({ sampleId: "S1", targetGroup: "G1", experimentId: "a" }),
        item({ sampleId: "S1", targetGroup: "G1", experimentId: "b" }),
        item({ sampleId: "S2", targetGroup: "G1", experimentId: "c" }),
      ];
      const out = normalizeDependencyItemsForSubmit(items);
      expect(out.map((i) => i.targetGroup)).toEqual(["G1", "G1", "G2"]);
      expect(out.map((i) => i.experimentId)).toEqual(["a", "b", "c"]);
    });

    it("drops non-experiment items", () => {
      const items = [item({ sampleId: "S1", labId: "", experimentId: "" })];
      expect(normalizeDependencyItemsForSubmit(items)).toEqual([]);
    });
  });

  describe("getEmptyDependencyFlowNames", () => {
    it("names flows that contain no experiment items", () => {
      const items = [item({ sampleId: "S1", labId: "", experimentId: "" })];
      expect(getEmptyDependencyFlowNames(items)).toEqual(["相依流程 1"]);
    });

    it("returns [] when every flow has experiments", () => {
      const items = [item({ sampleId: "S1", experimentId: "a" })];
      expect(getEmptyDependencyFlowNames(items)).toEqual([]);
    });
  });
});
