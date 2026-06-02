import { describe, expect, it } from "vitest";

import { bannerStyle } from "./styles";
import * as styles from "./styles";

describe("execution page style contract", () => {
  it("KPI grid renders five equal columns", () => {
    expect(styles.kpiGridStyle.display).toBe("grid");
    expect(String(styles.kpiGridStyle.gridTemplateColumns)).toBe("repeat(5,1fr)");
  });

  it("page header lays title and subtitle vertically with spacing", () => {
    expect(styles.pageHeaderStyle).toBeTypeOf("object");
    expect(styles.pageTitleStyle.fontWeight).toBeDefined();
  });

  describe("bannerStyle(ok)", () => {
    it("uses the green palette for success", () => {
      expect(bannerStyle(true).color).toBe("var(--green)");
      expect(String(bannerStyle(true).border)).toContain("63,185,80");
    });
    it("uses the red palette for failure", () => {
      expect(bannerStyle(false).color).toBe("var(--red)");
      expect(String(bannerStyle(false).border)).toContain("255,68,68");
    });
  });
});
