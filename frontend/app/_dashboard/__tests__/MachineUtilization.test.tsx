import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MachineUtilization from "../MachineUtilization";
import type { MachineHeatmap as Data, MachineGrid } from "@/types/dashboard";

function machine(overrides: Partial<MachineGrid>): MachineGrid {
  return {
    machine_id: "m1",
    machine_no: "M1",
    lab_name: "LAB-A",
    status: "in_use",
    today_hours: 0,
    current_recipe: null,
    current_operator: null,
    est_completion_at: null,
    ...overrides,
  };
}

const data: Data = {
  by_lab: {
    "LAB-A": [
      machine({
        machine_id: "m1",
        machine_no: "AFM-001",
        status: "in_use",
        today_hours: 5.2,
      }),
      machine({
        machine_id: "m2",
        machine_no: "AFM-002",
        status: "faulty",
        today_hours: 0,
      }),
      machine({
        machine_id: "m3",
        machine_no: "AFM-003",
        status: "disabled",
        today_hours: 0,
      }),
      machine({
        machine_id: "m4",
        machine_no: "AFM-004",
        status: "idle",
        today_hours: 0,
      }),
      machine({
        machine_id: "m5",
        machine_no: "XRD-001",
        status: "maintenance",
        today_hours: 1.6,
      }),
    ],
  },
  avg_utilization_pct: 53,
  in_use_count: 1,
  total_count: 5,
  per_lab_util_pct: { "LAB-A": 53 },
};

describe("MachineUtilization", () => {
  it("renders header avg util and in_use counts", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    const header = screen.getByText(/avg util 53% · in_use 1\/5/);
    expect(header).toBeInTheDocument();
  });

  it("renders one row per machine", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    expect(screen.getByTestId("machine-row-m1")).toBeInTheDocument();
    expect(screen.getByTestId("machine-row-m2")).toBeInTheDocument();
    expect(screen.getByTestId("machine-row-m3")).toBeInTheDocument();
    expect(screen.getByTestId("machine-row-m4")).toBeInTheDocument();
    expect(screen.getByTestId("machine-row-m5")).toBeInTheDocument();
  });

  it("renders machine_no for each row", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    expect(screen.getByText("AFM-001")).toBeInTheDocument();
    expect(screen.getByText("AFM-002")).toBeInTheDocument();
    expect(screen.getByText("XRD-001")).toBeInTheDocument();
  });

  it("computes util% from today_hours / 8 * 100 for in_use", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    // 5.2 / 8 * 100 = 65, rounded
    const fill = screen.getByTestId("machine-bar-fill-m1");
    expect(fill.style.width).toBe("65%");
    expect(fill.style.background).toContain("var(--blue)");
  });

  it("renders 0% width for idle with no hours", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    const fill = screen.getByTestId("machine-bar-fill-m4");
    expect(fill.style.width).toBe("0%");
    expect(fill.style.background).toContain("var(--text3)");
  });

  it("uses orange for maintenance util fill", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    const fill = screen.getByTestId("machine-bar-fill-m5");
    // 1.6 / 8 * 100 = 20
    expect(fill.style.width).toBe("20%");
    expect(fill.style.background).toContain("var(--orange)");
  });

  it("renders faulty row with red diagonal stripe pattern, util shown as —", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    const fill = screen.getByTestId("machine-bar-fill-m2");
    expect(fill.style.background).toContain("repeating-linear-gradient");
    expect(fill.style.background).toContain("45deg");
    expect(fill.style.background).toContain("var(--red)");
    // Confirm utility column shows em-dash for non-reporting status.
    const row = screen.getByTestId("machine-row-m2");
    expect(row.textContent).toContain("—");
    expect(row.textContent).not.toContain("%");
  });

  it("renders disabled row with gray diagonal stripe pattern, util shown as —", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    const fill = screen.getByTestId("machine-bar-fill-m3");
    expect(fill.style.background).toContain("repeating-linear-gradient");
    expect(fill.style.background).toContain("45deg");
    // jsdom normalizes #3a3a3a → rgb(58, 58, 58).
    expect(fill.style.background).toContain("rgb(58, 58, 58)");
    const row = screen.getByTestId("machine-row-m3");
    expect(row.textContent).toContain("—");
  });

  it("shows status labels in Chinese", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    expect(screen.getByText("使用中")).toBeInTheDocument();
    expect(screen.getByText("故障中")).toBeInTheDocument();
    expect(screen.getByText("停用")).toBeInTheDocument();
    expect(screen.getByText("閒置")).toBeInTheDocument();
    expect(screen.getByText("保養中")).toBeInTheDocument();
  });

  it("shows lab prefix when showLabPrefix=true", () => {
    render(<MachineUtilization data={data} showLabPrefix={true} />);
    // 5 rows × LAB-A lab prefix
    expect(screen.getAllByText("LAB-A").length).toBe(5);
  });

  it("hides lab prefix when showLabPrefix=false", () => {
    render(<MachineUtilization data={data} showLabPrefix={false} />);
    expect(screen.queryByText("LAB-A")).not.toBeInTheDocument();
  });

  it("shows empty state when total_count is 0", () => {
    render(
      <MachineUtilization
        data={{
          by_lab: {},
          avg_utilization_pct: 0,
          in_use_count: 0,
          total_count: 0,
          per_lab_util_pct: {},
        }}
        showLabPrefix={true}
      />
    );
    expect(screen.getByText("無機台資料")).toBeInTheDocument();
  });

  it("caps util% at 100 even when today_hours exceeds 8", () => {
    const overworked: Data = {
      by_lab: {
        "LAB-A": [
          machine({
            machine_id: "m9",
            machine_no: "X-9",
            status: "in_use",
            today_hours: 12,
          }),
        ],
      },
      avg_utilization_pct: 100,
      in_use_count: 1,
      total_count: 1,
      per_lab_util_pct: { "LAB-A": 100 },
    };
    render(<MachineUtilization data={overworked} showLabPrefix={false} />);
    const fill = screen.getByTestId("machine-bar-fill-m9");
    expect(fill.style.width).toBe("100%");
  });
});
