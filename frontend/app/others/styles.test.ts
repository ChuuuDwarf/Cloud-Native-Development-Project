import { describe, expect, it } from "vitest";

import * as styles from "./styles";

describe("others page style contract", () => {
  it("current-user layout caps the side column width with minmax", () => {
    expect(styles.currentUserGridStyle.display).toBe("grid");
    expect(String(styles.currentUserGridStyle.gridTemplateColumns)).toBe("1fr minmax(280px, 420px)");
  });

  it("form / matrix / master grids are responsive auto-fit grids", () => {
    for (const style of [styles.formGridStyle, styles.experimentMatrixStyle, styles.masterGridStyle]) {
      expect(style.display).toBe("grid");
      expect(String(style.gridTemplateColumns)).toContain("auto-fit");
      expect(String(style.gridTemplateColumns)).toContain("minmax");
    }
  });

  it("exports only style objects", () => {
    for (const [name, value] of Object.entries(styles)) {
      expect(typeof value, name).toBe("object");
    }
  });
});
