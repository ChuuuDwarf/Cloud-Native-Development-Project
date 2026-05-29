import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MachineHeatmap from "../MachineHeatmap";
import type { MachineHeatmap as Data } from "@/types/dashboard";

const data: Data = {
  by_lab: {
    "LAB-A": [
      {
        machine_id: "m1",
        machine_no: "M1",
        lab_name: "LAB-A",
        status: "in_use",
        today_hours: 3.2,
        current_recipe: null,
        current_operator: null,
        est_completion_at: null,
      },
      {
        machine_id: "m2",
        machine_no: "M2",
        lab_name: "LAB-A",
        status: "faulty",
        today_hours: 0,
        current_recipe: null,
        current_operator: null,
        est_completion_at: null,
      },
    ],
  },
  avg_utilization_pct: 67,
  in_use_count: 1,
  total_count: 2,
};

describe("MachineHeatmap", () => {
  it("renders header with util + counts", () => {
    render(<MachineHeatmap data={data} showLabPrefix={true} />);
    expect(screen.getByText(/avg util 67%/)).toBeInTheDocument();
    expect(screen.getByText(/in_use 1\/2/)).toBeInTheDocument();
  });

  it("shows lab prefix when enabled", () => {
    render(<MachineHeatmap data={data} showLabPrefix={true} />);
    expect(screen.getByText("LAB-A")).toBeInTheDocument();
  });

  it("hides lab prefix when disabled (lab_supervisor)", () => {
    render(<MachineHeatmap data={data} showLabPrefix={false} />);
    expect(screen.queryByText("LAB-A")).not.toBeInTheDocument();
  });

  it("shows empty state when no machines", () => {
    render(
      <MachineHeatmap
        data={{ by_lab: {}, avg_utilization_pct: 0, in_use_count: 0, total_count: 0 }}
        showLabPrefix={true}
      />
    );
    expect(screen.getByText("無機台資料")).toBeInTheDocument();
  });
});
