import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import LabLeaderboard from "../LabLeaderboard";
import type { LabRow } from "@/types/dashboard";

const rows: LabRow[] = [
  {
    lab_name: "LAB-A",
    completed_today: 9,
    awaiting_handoff: 2,
    open_high_critical_issues: 1,
    avg_utilization_pct: 78,
    trend_24h: "up",
  },
  {
    lab_name: "LAB-B",
    completed_today: 4,
    awaiting_handoff: 1,
    open_high_critical_issues: 0,
    avg_utilization_pct: 58,
    trend_24h: "flat",
  },
  {
    lab_name: "LAB-C",
    completed_today: 5,
    awaiting_handoff: 3,
    open_high_critical_issues: 2,
    avg_utilization_pct: 72,
    trend_24h: "down",
  },
];

describe("LabLeaderboard", () => {
  it("renders 4 sub-charts with metric titles", () => {
    render(<LabLeaderboard rows={rows} />);
    expect(screen.getByText("完工(綠)")).toBeInTheDocument();
    expect(screen.getByText("待傳(橙)")).toBeInTheDocument();
    expect(screen.getByText("告警(紅)")).toBeInTheDocument();
    expect(screen.getByText("util%(藍)")).toBeInTheDocument();
  });

  it("emits a sub-chart container per metric", () => {
    render(<LabLeaderboard rows={rows} />);
    expect(screen.getByTestId("lab-subchart-completed_today")).toBeInTheDocument();
    expect(screen.getByTestId("lab-subchart-awaiting_handoff")).toBeInTheDocument();
    expect(screen.getByTestId("lab-subchart-open_high_critical_issues")).toBeInTheDocument();
    expect(screen.getByTestId("lab-subchart-avg_utilization_pct")).toBeInTheDocument();
  });

  it("sorts completed_today desc (highest first)", () => {
    render(<LabLeaderboard rows={rows} />);
    // LAB-A=9, LAB-C=5, LAB-B=4
    expect(screen.getByTestId("lab-subchart-completed_today").getAttribute("data-order")).toBe(
      "LAB-A,LAB-C,LAB-B"
    );
  });

  it("sorts open_high_critical_issues asc (fewest issues first)", () => {
    render(<LabLeaderboard rows={rows} />);
    // LAB-B=0, LAB-A=1, LAB-C=2
    expect(
      screen.getByTestId("lab-subchart-open_high_critical_issues").getAttribute("data-order")
    ).toBe("LAB-B,LAB-A,LAB-C");
  });

  it("sorts avg_utilization_pct desc", () => {
    render(<LabLeaderboard rows={rows} />);
    // LAB-A=78, LAB-C=72, LAB-B=58
    expect(
      screen.getByTestId("lab-subchart-avg_utilization_pct").getAttribute("data-order")
    ).toBe("LAB-A,LAB-C,LAB-B");
  });

  it("shows the empty dash when a metric is all zero", () => {
    const allZeroCompletions: LabRow[] = rows.map((r) => ({ ...r, completed_today: 0 }));
    render(<LabLeaderboard rows={allZeroCompletions} />);
    expect(screen.getByTestId("lab-subchart-empty-completed_today")).toBeInTheDocument();
  });

  it("shows the top-level empty state when no rows", () => {
    render(<LabLeaderboard rows={[]} />);
    expect(screen.getByText("無 lab 資料")).toBeInTheDocument();
  });
});
