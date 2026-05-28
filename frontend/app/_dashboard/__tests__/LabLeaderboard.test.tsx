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
];

describe("LabLeaderboard", () => {
  it("renders rows", () => {
    render(<LabLeaderboard rows={rows} />);
    expect(screen.getByText("LAB-A")).toBeInTheDocument();
    expect(screen.getByText(/完工 9/)).toBeInTheDocument();
    expect(screen.getByText(/util 78%/)).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<LabLeaderboard rows={[]} />);
    expect(screen.getByText("無 lab 資料")).toBeInTheDocument();
  });
});
