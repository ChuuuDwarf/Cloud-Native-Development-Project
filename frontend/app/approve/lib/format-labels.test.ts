import { describe, expect, it } from "vitest";

import { actionLabel, priorityLabel, statusLabel } from "./labels";
import { formatDate } from "./format";

describe("approve/lib/format", () => {
  it("returns '-' for nullish, raw for invalid, formatted for valid", () => {
    expect(formatDate()).toBe("-");
    expect(formatDate(null)).toBe("-");
    expect(formatDate("nope")).toBe("nope");
    expect(formatDate("2026-05-01T08:00:00")).toContain("2026");
  });
});

describe("approve/lib/labels", () => {
  it("maps known order statuses", () => {
    expect(statusLabel.draft).toBe("草稿");
    expect(statusLabel.pending_approval).toBe("待簽核");
    expect(statusLabel.closed).toBe("已結案");
  });

  it("maps priorities", () => {
    expect(priorityLabel.normal).toBe("一般");
    expect(priorityLabel.urgent).toBe("急件");
    expect(priorityLabel.critical).toBe("特急件");
  });

  it("maps actions", () => {
    expect(actionLabel.approve).toBe("核准");
    expect(actionLabel.return).toBe("退回補件");
    expect(actionLabel.reject).toBe("拒絕");
  });
});
