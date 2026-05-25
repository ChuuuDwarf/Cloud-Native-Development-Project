import { describe, expect, it } from "vitest";

import { summaryGridStyle, twoColumnGridStyle } from "./styles";

describe("transfer RWD style contract", () => {
  it("交接摘要卡片使用 auto-fit grid 支援響應式欄位", () => {
    expect(summaryGridStyle.display).toBe("grid");
    expect(String(summaryGridStyle.gridTemplateColumns)).toContain("auto-fit");
    expect(String(summaryGridStyle.gridTemplateColumns)).toContain("minmax");
  });

  it("主要交接候選區保留雙欄 grid 的最小寬度規則", () => {
    expect(twoColumnGridStyle.display).toBe("grid");
    expect(String(twoColumnGridStyle.gridTemplateColumns)).toContain("minmax(360px, 1fr)");
  });
});
