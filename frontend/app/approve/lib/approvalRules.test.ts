import { describe, expect, it } from "vitest";

import type { Order, OrderItem } from "../types";
import {
  approvableItemsForActor,
  canActorApproveItem,
  getEffectiveItemStatus,
  isHighPriority,
  itemNeedsQuotaOverride,
  orderHasQuotaExceededReason,
  quotaStatusText,
  sortApprovalOrders,
} from "./approvalRules";

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 1,
    orderNo: "ORD-1",
    applicantId: "u1",
    departmentId: "d1",
    applyDate: "2026-01-01T00:00:00",
    status: "pending_approval",
    priority: "normal",
    totalItems: 1,
    createdAt: "2026-01-01T00:00:00",
    updatedAt: "2026-01-01T00:00:00",
    ...overrides,
  };
}

function makeItem(overrides: Partial<OrderItem> = {}): OrderItem {
  return {
    id: 10,
    sampleId: "SMP-1",
    labId: "lab-1",
    experimentId: "exp-1",
    targetGroup: "G1",
    target: 1,
    check: false,
    ...overrides,
  };
}

describe("approve/lib/approvalRules", () => {
  describe("sortApprovalOrders", () => {
    it("orders by priority rank then newest applyDate, without mutating input", () => {
      const orders = [
        makeOrder({ id: 1, priority: "normal", applyDate: "2026-01-01T00:00:00" }),
        makeOrder({ id: 2, priority: "critical", applyDate: "2026-01-01T00:00:00" }),
        makeOrder({ id: 3, priority: "urgent", applyDate: "2026-02-01T00:00:00" }),
        makeOrder({ id: 4, priority: "urgent", applyDate: "2026-03-01T00:00:00" }),
      ];
      const sorted = sortApprovalOrders(orders);
      expect(sorted.map((o) => o.id)).toEqual([2, 4, 3, 1]);
      // input untouched
      expect(orders.map((o) => o.id)).toEqual([1, 2, 3, 4]);
    });

    it("defaults missing priority to normal", () => {
      const orders = [
        makeOrder({ id: 1, priority: undefined, applyDate: "2026-01-01T00:00:00" }),
        makeOrder({ id: 2, priority: "critical", applyDate: "2026-01-01T00:00:00" }),
      ];
      expect(sortApprovalOrders(orders).map((o) => o.id)).toEqual([2, 1]);
    });
  });

  describe("isHighPriority", () => {
    it("is true for critical and urgent only", () => {
      expect(isHighPriority("critical")).toBe(true);
      expect(isHighPriority("urgent")).toBe(true);
      expect(isHighPriority("normal")).toBe(false);
      expect(isHighPriority(undefined)).toBe(false);
    });
  });

  describe("getEffectiveItemStatus", () => {
    it("upgrades draft/empty to pending_approval when order is pending", () => {
      const order = makeOrder({ status: "pending_approval" });
      expect(getEffectiveItemStatus(order, makeItem({ status: undefined }))).toBe(
        "pending_approval"
      );
      expect(getEffectiveItemStatus(order, makeItem({ status: "draft" }))).toBe("pending_approval");
    });

    it("passes through other statuses", () => {
      const order = makeOrder({ status: "approved" });
      expect(getEffectiveItemStatus(order, makeItem({ status: "approved" }))).toBe("approved");
      expect(getEffectiveItemStatus(order, makeItem({ status: undefined }))).toBe("-");
    });
  });

  describe("canActorApproveItem", () => {
    it("allows when order pending, actor owns lab, and item effective status pending", () => {
      const order = makeOrder({ status: "pending_approval" });
      const item = makeItem({ labId: "lab-1", status: "draft" });
      expect(canActorApproveItem(["lab-1"], order, item)).toBe(true);
    });

    it("denies when actor does not own the item lab", () => {
      const order = makeOrder({ status: "pending_approval" });
      const item = makeItem({ labId: "lab-9", status: "draft" });
      expect(canActorApproveItem(["lab-1"], order, item)).toBe(false);
    });

    it("denies when order is not pending", () => {
      const order = makeOrder({ status: "approved" });
      const item = makeItem({ labId: "lab-1", status: "approved" });
      expect(canActorApproveItem(["lab-1"], order, item)).toBe(false);
    });
  });

  describe("orderHasQuotaExceededReason", () => {
    it("detects 配額 / 超額 keywords in lastReason", () => {
      expect(orderHasQuotaExceededReason(makeOrder({ lastReason: "配額不足" }))).toBe(true);
      expect(orderHasQuotaExceededReason(makeOrder({ lastReason: "已超額" }))).toBe(true);
      expect(orderHasQuotaExceededReason(makeOrder({ lastReason: "其他原因" }))).toBe(false);
      expect(orderHasQuotaExceededReason(makeOrder({ lastReason: null }))).toBe(false);
    });
  });

  describe("itemNeedsQuotaOverride", () => {
    it("is false when already overridden", () => {
      expect(itemNeedsQuotaOverride(makeOrder(), makeItem({ quotaOverride: true }))).toBe(false);
    });

    it("uses item quotaExceeded flag when present", () => {
      expect(itemNeedsQuotaOverride(makeOrder(), makeItem({ quotaExceeded: true }))).toBe(true);
      expect(itemNeedsQuotaOverride(makeOrder(), makeItem({ quotaExceeded: false }))).toBe(false);
    });

    it("falls back to order reason when item flag absent", () => {
      const order = makeOrder({ lastReason: "配額超過" });
      expect(itemNeedsQuotaOverride(order, makeItem({ quotaExceeded: undefined }))).toBe(true);
    });
  });

  describe("quotaStatusText", () => {
    it("covers all three branches", () => {
      expect(quotaStatusText(makeOrder(), makeItem({ quotaOverride: true }))).toBe("配額：已特批");
      expect(quotaStatusText(makeOrder(), makeItem({ quotaExceeded: true }))).toBe("配額：需特批");
      expect(quotaStatusText(makeOrder(), makeItem())).toBe("配額：正常");
    });
  });

  describe("approvableItemsForActor", () => {
    it("filters to items the actor can approve", () => {
      const order = makeOrder({
        status: "pending_approval",
        items: [
          makeItem({ id: 1, labId: "lab-1", status: "draft" }),
          makeItem({ id: 2, labId: "lab-2", status: "draft" }),
          makeItem({ id: 3, labId: "lab-1", status: "approved" }),
        ],
      });
      expect(approvableItemsForActor(["lab-1"], order).map((i) => i.id)).toEqual([1]);
    });

    it("returns empty when order has no items", () => {
      expect(approvableItemsForActor(["lab-1"], makeOrder({ items: undefined }))).toEqual([]);
    });
  });
});
