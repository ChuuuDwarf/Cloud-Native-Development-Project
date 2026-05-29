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
  per_lab_util_pct: { "LAB-A": 78 },
};

describe("MachineHeatmap", () => {
  it("renders header counts", () => {
    render(<MachineHeatmap data={data} showLabPrefix={true} />);
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

  describe("RadialGauge color thresholds", () => {
    const renderWithUtil = (pct: number) =>
      render(
        <MachineHeatmap
          data={{ ...data, avg_utilization_pct: pct }}
          showLabPrefix={true}
        />
      );

    it("uses text3 grey when util < 40", () => {
      const { getByTestId } = renderWithUtil(20);
      expect(getByTestId("radial-gauge").getAttribute("data-util-color")).toBe("var(--text3)");
    });

    it("uses blue when util in [40, 80)", () => {
      const { getByTestId } = renderWithUtil(67);
      expect(getByTestId("radial-gauge").getAttribute("data-util-color")).toBe("var(--blue)");
    });

    it("uses orange when util in [80, 95)", () => {
      const { getByTestId } = renderWithUtil(85);
      expect(getByTestId("radial-gauge").getAttribute("data-util-color")).toBe("var(--orange)");
    });

    it("uses red when util >= 95", () => {
      const { getByTestId } = renderWithUtil(98);
      expect(getByTestId("radial-gauge").getAttribute("data-util-color")).toBe("var(--red)");
    });
  });

  describe("per-lab mini util bar", () => {
    it("renders mini bar with width proportional to util", () => {
      render(<MachineHeatmap data={data} showLabPrefix={true} />);
      const fill = screen.getByTestId("lab-mini-util-fill");
      // 78% of a 20px-wide bar = round(15.6) = 16px
      expect(fill.getAttribute("data-fill-px")).toBe("16");
      expect(screen.getByText("78%")).toBeInTheDocument();
    });

    it("does not render mini bar when lab's util is undefined", () => {
      const noUtil: Data = {
        ...data,
        per_lab_util_pct: {},
      };
      render(<MachineHeatmap data={noUtil} showLabPrefix={true} />);
      expect(screen.queryByTestId("lab-mini-util")).not.toBeInTheDocument();
    });
  });
});
