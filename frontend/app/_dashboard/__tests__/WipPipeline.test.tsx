import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import WipPipeline from "../WipPipeline";
import type { WipPipeline as Data } from "@/types/dashboard";

const data: Data = {
  total: 31,
  waiting_dispatch: [5, 1],
  dispatched: [3, 0],
  in_progress: [12, -2],
  awaiting_handoff: [8, 3],
  done: [3, 1],
  terminated: [0, 0],
};

describe("WipPipeline", () => {
  it("renders header with total", () => {
    render(<WipPipeline data={data} />);
    // Header lives next to the section title; donut center repeats it.
    const matches = screen.getAllByText(/共 31 件/);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("renders the donut center label with total", () => {
    render(<WipPipeline data={data} />);
    const center = screen.getByTestId("wip-donut-total");
    expect(center.textContent).toContain("31");
  });

  it("shows all 6 stage labels in the legend with counts", () => {
    render(<WipPipeline data={data} />);
    for (const stageKey of [
      "waiting_dispatch",
      "dispatched",
      "in_progress",
      "awaiting_handoff",
      "done",
      "terminated",
    ] as const) {
      expect(screen.getByTestId(`wip-legend-${stageKey}`)).toBeInTheDocument();
    }
    // Labels render
    expect(screen.getByText("待排程")).toBeInTheDocument();
    expect(screen.getByText("排程")).toBeInTheDocument();
    expect(screen.getByText("進行")).toBeInTheDocument();
    expect(screen.getByText("待傳")).toBeInTheDocument();
    expect(screen.getByText("完")).toBeInTheDocument();
    expect(screen.getByText("終止")).toBeInTheDocument();
  });

  it("legend rows show correct counts", () => {
    render(<WipPipeline data={data} />);
    const inProgress = screen.getByTestId("wip-legend-in_progress");
    expect(inProgress.textContent).toContain("進行");
    expect(inProgress.textContent).toContain("12");
    const done = screen.getByTestId("wip-legend-done");
    expect(done.textContent).toContain("3");
  });

  it("shows empty state when total = 0", () => {
    render(
      <WipPipeline
        data={{
          total: 0,
          waiting_dispatch: [0, 0],
          dispatched: [0, 0],
          in_progress: [0, 0],
          awaiting_handoff: [0, 0],
          done: [0, 0],
          terminated: [0, 0],
        }}
      />
    );
    expect(screen.getByText("目前無 WIP")).toBeInTheDocument();
    // Donut should not render in empty state.
    expect(screen.queryByTestId("wip-donut")).not.toBeInTheDocument();
  });

  it("renders delta arrows with correct direction", () => {
    render(<WipPipeline data={data} />);
    const waiting = screen.getByTestId("wip-legend-waiting_dispatch");
    // 1 → up arrow
    expect(waiting.textContent).toContain("↑1");
    const inProgress = screen.getByTestId("wip-legend-in_progress");
    // -2 → down arrow
    expect(inProgress.textContent).toContain("↓2");
    const dispatched = screen.getByTestId("wip-legend-dispatched");
    // 0 → flat arrow
    expect(dispatched.textContent).toContain("→");
  });

  describe("legend click drilling", () => {
    let originalLocation: Location;
    beforeEach(() => {
      originalLocation = window.location;
      // jsdom forbids reassigning window.location directly; redefine the
      // property so we can spy on assignments to .href.
      Object.defineProperty(window, "location", {
        configurable: true,
        value: { ...originalLocation, href: "" },
      });
    });
    afterEach(() => {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    });

    it("clicking a legend row drills to its path", () => {
      render(<WipPipeline data={data} />);
      fireEvent.click(screen.getByTestId("wip-legend-in_progress"));
      expect(window.location.href).toBe("/execution");
    });

    it("clicking 終止 legend drills to terminated orders", () => {
      render(<WipPipeline data={data} />);
      fireEvent.click(screen.getByTestId("wip-legend-terminated"));
      expect(window.location.href).toBe("/orders?status=terminated");
    });

    it("clicking 完 legend drills to /storage", () => {
      render(<WipPipeline data={data} />);
      fireEvent.click(screen.getByTestId("wip-legend-done"));
      expect(window.location.href).toBe("/storage");
    });
  });

  // Note: the inline SVG <defs> for the donut pattern is rendered inside
  // Recharts' <PieChart>, which only mounts its SVG once ResponsiveContainer
  // measures non-zero dimensions. jsdom reports width=-1 for the container,
  // so the chart (and its <defs>) never reach the DOM in this environment.
  // The pattern fill is verified visually in the real browser; here we just
  // assert the legend swatch shows the stripe styling so users still see the
  // "terminated is special" cue even if their browser fails to render the
  // pattern.

  it("terminated legend swatch uses the stripe gradient", () => {
    const withTerminated: Data = {
      ...data,
      total: 35,
      terminated: [4, 0],
    };
    render(<WipPipeline data={withTerminated} />);
    const swatch = screen.getByTestId("wip-legend-swatch-terminated");
    expect(swatch.style.background).toContain("repeating-linear-gradient");
    expect(swatch.style.background).toContain("45deg");
  });
});
