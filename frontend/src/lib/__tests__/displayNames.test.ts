import { describe, expect, it } from "vitest";
import {
  displayDepartmentName,
  displayExperimentName,
  displayLabName,
  displayScopeName,
  displayUserName,
} from "@/lib/displayNames";

const masterData = {
  departments: [{ id: "dep-1", code: "D1", name: "製程部" }],
  labs: [{ id: "lab-1", code: "L1", name: "材料分析實驗室" }],
  experiments: [{ id: "exp-1", labId: "lab-1", name: "SEM" }],
};

describe("displayNames", () => {
  it("displays users, current user fallback, and empty values", () => {
    expect(displayUserName(null, {})).toBe("-");
    expect(displayUserName("u-1", {}, { id: "u-1", name: "" })).toBe("目前使用者");
    expect(displayUserName("u-2", { "u-2": "Alice" })).toBe("Alice");
    expect(displayUserName("missing", {})).toBe("未知使用者");
  });

  it("displays department, lab, and experiment names by id or code", () => {
    expect(displayDepartmentName(masterData, "dep-1")).toBe("製程部");
    expect(displayDepartmentName(masterData, "D1")).toBe("製程部");
    expect(displayDepartmentName(masterData, undefined)).toBe("-");
    expect(displayDepartmentName(masterData, "nope")).toBe("未知部門");

    expect(displayLabName(masterData, "lab-1")).toBe("材料分析實驗室");
    expect(displayLabName(masterData, "L1")).toBe("材料分析實驗室");
    expect(displayLabName(masterData, "")).toBe("-");
    expect(displayLabName(masterData, "nope")).toBe("未知實驗室");

    expect(displayExperimentName(masterData, "exp-1")).toBe("SEM");
    expect(displayExperimentName(masterData, null)).toBe("-");
    expect(displayExperimentName(masterData, "nope")).toBe("未知實驗");
  });

  it("dispatches scope display by scope type", () => {
    expect(displayScopeName(masterData, { "u-1": "Alice" }, "user", "u-1")).toBe("Alice");
    expect(displayScopeName(masterData, {}, "department", "D1")).toBe("製程部");
    expect(displayScopeName(masterData, {}, "lab", "L1")).toBe("材料分析實驗室");
    expect(displayScopeName(masterData, {}, "unknown", "raw")).toBe("raw");
    expect(displayScopeName(masterData, {}, "unknown", "")).toBe("-");
  });
});
