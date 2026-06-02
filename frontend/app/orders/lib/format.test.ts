import { describe, expect, it } from "vitest";

import type { Order, OrderItem } from "../types";
import { formatDate, getEffectiveItemStatus, quotaStatusText } from "./format";

const baseOrder: Order = {
  id: 1,
  orderNo: "ORD-1",
  applicantId: "u1",
  departmentId: "d1",
  applyDate: "2026-01-01T00:00:00",
  status: "draft",
  totalItems: 1,
  createdAt: "2026-01-01T00:00:00",
  updatedAt: "2026-01-01T00:00:00",
};

const baseItem: OrderItem = {
  id: 10,
  sampleId: "SMP-1",
  labId: "lab-1",
  experimentId: "exp-1",
  targetGroup: "G1",
  target: 1,
  check: false,
};

describe("orders/lib/format", () => {
  describe("formatDate", () => {
    it("returns '-' for nullish input", () => {
      expect(formatDate()).toBe("-");
      expect(formatDate(null)).toBe("-");
      expect(formatDate("")).toBe("-");
    });

    it("returns the raw string for unparseable dates", () => {
      expect(formatDate("not-a-date")).toBe("not-a-date");
    });

    it("formats a valid ISO date in zh-TW locale", () => {
      const result = formatDate("2026-01-02T03:04:00");
      // Locale formatting differs by platform; assert it contains the parts.
      expect(result).toContain("2026");
      expect(result).not.toBe("-");
      expect(result).not.toBe("2026-01-02T03:04:00");
    });
  });

  describe("getEffectiveItemStatus", () => {
    it("maps draft/empty item status to pending_approval when order awaits approval", () => {
      const order = { ...baseOrder, status: "pending_approval" as const };
      expect(getEffectiveItemStatus(order, { ...baseItem, status: undefined })).toBe(
        "pending_approval"
      );
      expect(getEffectiveItemStatus(order, { ...baseItem, status: "draft" })).toBe(
        "pending_approval"
      );
    });

    it("returns the item status verbatim otherwise", () => {
      expect(getEffectiveItemStatus(baseOrder, { ...baseItem, status: "approved" })).toBe(
        "approved"
      );
    });

    it("returns '-' when item has no status and order is not pending", () => {
      expect(getEffectiveItemStatus(baseOrder, { ...baseItem, status: undefined })).toBe("-");
    });
  });

  describe("quotaStatusText", () => {
    it("reports already-overridden quota", () => {
      expect(quotaStatusText({ ...baseItem, quotaOverride: true })).toBe("配額：已特批");
    });

    it("reports quota exceeded needing override", () => {
      expect(quotaStatusText({ ...baseItem, quotaExceeded: true })).toBe("配額：需特批");
    });

    it("reports normal quota", () => {
      expect(quotaStatusText(baseItem)).toBe("配額：正常");
    });
  });
});
