import { describe, expect, it } from "vitest";

import { buttonStyle, filterTabStyle } from "./styles";
import * as styles from "./styles";

describe("orders page style contract", () => {
  it("workspace uses a fixed sidebar + fluid content two-column grid", () => {
    expect(styles.workspaceStyle.display).toBe("grid");
    expect(String(styles.workspaceStyle.gridTemplateColumns)).toBe("340px 1fr");
  });

  it("order workspace grid keeps the content column collapsible (minmax(0,1fr))", () => {
    expect(styles.orderWorkspaceGridStyle.display).toBe("grid");
    expect(String(styles.orderWorkspaceGridStyle.gridTemplateColumns)).toContain("minmax(0, 1fr)");
  });

  it("page header lays out title/actions on opposite ends", () => {
    expect(styles.pageHeaderStyle.display).toBe("flex");
    expect(styles.pageHeaderStyle.justifyContent).toBe("space-between");
  });

  describe("filterTabStyle(active)", () => {
    it("highlights the active tab with the blue accent and white text", () => {
      const active = filterTabStyle(true);
      expect(active.background).toBe("var(--blue)");
      expect(active.color).toBe("#fff");
    });
    it("renders inactive tabs in the muted surface palette", () => {
      const inactive = filterTabStyle(false);
      expect(inactive.background).toBe("var(--s2)");
      expect(inactive.color).toBe("var(--text2)");
    });
  });

  describe("buttonStyle(kind)", () => {
    it("maps each kind to its accent colour token", () => {
      expect(buttonStyle("blue").background).toBe("var(--blue)");
      expect(buttonStyle("green").background).toBe("var(--green)");
      expect(buttonStyle("gray").background).toBe("var(--s3)");
      expect(buttonStyle("red").background).toBe("var(--red)");
    });
    it("uses muted text for the gray kind and white otherwise", () => {
      expect(buttonStyle("gray").color).toBe("var(--text2)");
      expect(buttonStyle("blue").color).toBe("#fff");
    });
  });
});
