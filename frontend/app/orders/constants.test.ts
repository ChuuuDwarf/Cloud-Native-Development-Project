import { describe, expect, it } from "vitest";

import {
  actionLabel,
  allowedActions,
  emptyFormItem,
  emptyMasterData,
  orderStatusFilters,
  priorityLabel,
  statusLabel,
} from "./constants";

describe("orders constants", () => {
  it("emptyFormItem is a blank G1 item", () => {
    expect(emptyFormItem).toMatchObject({ targetGroup: "G1", target: 1, check: false });
  });

  it("emptyMasterData has empty collections", () => {
    expect(emptyMasterData.departments).toEqual([]);
    expect(emptyMasterData.labs).toEqual([]);
    expect(emptyMasterData.experiments).toEqual([]);
  });

  it("every allowedActions value references a labelled action", () => {
    for (const actions of Object.values(allowedActions)) {
      for (const action of actions) {
        expect(actionLabel[action]).toBeDefined();
      }
    }
  });

  it("draft and returned orders can be submitted or cancelled; terminal states have no actions", () => {
    expect(allowedActions.draft).toEqual(["submit", "cancel"]);
    expect(allowedActions.returned).toEqual(["submit", "cancel"]);
    expect(allowedActions.closed).toEqual([]);
    expect(allowedActions.cancelled).toEqual([]);
    expect(allowedActions.rejected).toEqual([]);
  });

  it("status filter values (except 'all') all have a status label", () => {
    for (const filter of orderStatusFilters) {
      if (filter.value === "all") continue;
      expect(statusLabel[filter.value]).toBeDefined();
    }
  });

  it("priority labels cover the core priorities", () => {
    expect(priorityLabel.normal).toBe("一般");
    expect(priorityLabel.urgent).toBeDefined();
    expect(priorityLabel.critical).toBeDefined();
  });
});
