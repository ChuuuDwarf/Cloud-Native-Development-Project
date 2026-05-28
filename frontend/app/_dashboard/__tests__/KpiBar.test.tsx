import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import KpiBar from "../KpiBar";
import type { KpiBar as KpiBarData } from "@/types/dashboard";

const mk = (v: number, d: number = 0): KpiBarData["new_orders"] => ({
  value: v,
  delta_24h: d,
  threshold_color: "neutral",
});

const data: KpiBarData = {
  new_orders: mk(12, 3),
  completed: mk(9, -1),
  returned: mk(4, 0),
  pending_approval: { value: 7, delta_24h: 0, threshold_color: "orange" },
  open_critical_high_issues: { value: 2, delta_24h: 0, threshold_color: "red" },
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
});
