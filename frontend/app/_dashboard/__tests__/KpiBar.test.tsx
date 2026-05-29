import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import KpiBar from "../KpiBar";
import type { KpiBar as KpiBarData, KpiCardData } from "@/types/dashboard";

const mk = (
  v: number,
  d: number = 0,
  sparkline: number[] | null = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1, 0]
): KpiCardData => ({
  value: v,
  delta_24h: d,
  threshold_color: "neutral",
  sparkline_24h: sparkline,
});

const data: KpiBarData = {
  new_orders: mk(12, 3),
  completed: mk(9, -1),
  returned: mk(4, 0),
  pending_approval: { value: 7, delta_24h: 0, threshold_color: "orange", sparkline_24h: null },
  open_critical_high_issues: {
    value: 2,
    delta_24h: 0,
    threshold_color: "red",
    sparkline_24h: null,
  },
};

describe("KpiBar", () => {
  it("renders 5 tiles", () => {
    render(<KpiBar data={data} />);
    expect(screen.getByText("新單")).toBeInTheDocument();
    expect(screen.getByText("完工")).toBeInTheDocument();
    expect(screen.getByText("回傳")).toBeInTheDocument();
    expect(screen.getByText("待簽")).toBeInTheDocument();
    expect(screen.getByText("告警")).toBeInTheDocument();
  });

  it("shows arrows: ↑ for positive, ↓ for negative, → for zero", () => {
    render(<KpiBar data={data} />);
    expect(screen.getByText("↑3")).toBeInTheDocument();
    expect(screen.getByText("↓1")).toBeInTheDocument();
    expect(screen.getAllByText("→").length).toBeGreaterThan(0);
  });

  it("displays all values", () => {
    render(<KpiBar data={data} />);
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders a sparkline for flow KPIs with non-zero history", () => {
    render(<KpiBar data={data} />);
    // 3 flow tiles (new_orders, completed, returned) have sparkline data;
    // 2 state tiles (pending_approval, open_critical_high_issues) pass null.
    expect(screen.getAllByTestId("kpi-sparkline")).toHaveLength(3);
  });

  it("does not render sparkline when sparkline_24h is null", () => {
    const allNull: KpiBarData = {
      new_orders: mk(0, 0, null),
      completed: mk(0, 0, null),
      returned: mk(0, 0, null),
      pending_approval: { value: 0, delta_24h: 0, threshold_color: "neutral", sparkline_24h: null },
      open_critical_high_issues: {
        value: 0,
        delta_24h: 0,
        threshold_color: "neutral",
        sparkline_24h: null,
      },
    };
    render(<KpiBar data={allNull} />);
    expect(screen.queryAllByTestId("kpi-sparkline")).toHaveLength(0);
  });

  it("does not render sparkline when every bucket is zero", () => {
    const zeros = new Array(24).fill(0);
    const allZero: KpiBarData = {
      new_orders: mk(0, 0, zeros),
      completed: mk(0, 0, zeros),
      returned: mk(0, 0, zeros),
      pending_approval: { value: 0, delta_24h: 0, threshold_color: "neutral", sparkline_24h: null },
      open_critical_high_issues: {
        value: 0,
        delta_24h: 0,
        threshold_color: "neutral",
        sparkline_24h: null,
      },
    };
    render(<KpiBar data={allZero} />);
    expect(screen.queryAllByTestId("kpi-sparkline")).toHaveLength(0);
  });
});
