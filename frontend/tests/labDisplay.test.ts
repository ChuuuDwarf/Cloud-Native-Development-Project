import { describe, expect, it } from "vitest";

import { formatLab, labNames } from "@/components/labDisplay";

describe("labDisplay", () => {
  it("contains the known lab display names", () => {
    expect(labNames).toEqual({
      "LAB-A": "材料分析實驗室",
      "LAB-B": "結構分析實驗室",
      "LAB-C": "光學量測實驗室",
    });
  });

  it("formats a known lab with its Chinese name", () => {
    expect(formatLab("LAB-A")).toBe("LAB-A 材料分析實驗室");
  });

  it("formats an unknown lab without trailing whitespace", () => {
    expect(formatLab("LAB X")).toBe("LAB X");
  });

  it("uses global label for empty lab values", () => {
    expect(formatLab()).toBe("全 LAB");
    expect(formatLab(null)).toBe("全 LAB");
    expect(formatLab("")).toBe("全 LAB");
  });
});
