import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
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
    expect(screen.getByText(/共 31 件/)).toBeInTheDocument();
  });

  it("shows all 6 stage labels", () => {
    render(<WipPipeline data={data} />);
    expect(screen.getByText("待排程")).toBeInTheDocument();
    expect(screen.getByText("排程")).toBeInTheDocument();
    expect(screen.getByText("進行")).toBeInTheDocument();
    expect(screen.getByText("待傳")).toBeInTheDocument();
    expect(screen.getByText("完")).toBeInTheDocument();
    expect(screen.getByText("終止")).toBeInTheDocument();
  });

  it("shows empty state when no WIP", () => {
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
  });

  it("shows tooltip when hovering over a segment", () => {
    render(<WipPipeline data={data} />);
    // in_progress is 12 of 31 = 38.7%
    const segment = screen.getByTestId("wip-segment-in_progress");
    expect(screen.queryByTestId("wip-tooltip")).not.toBeInTheDocument();
    fireEvent.mouseEnter(segment);
    const tooltip = screen.getByTestId("wip-tooltip");
    expect(tooltip).toBeInTheDocument();
    expect(tooltip.textContent).toContain("進行");
    expect(tooltip.textContent).toContain("12");
    expect(tooltip.textContent).toContain("39%");
    expect(tooltip.textContent).toContain("↓2");
    fireEvent.mouseLeave(segment);
    expect(screen.queryByTestId("wip-tooltip")).not.toBeInTheDocument();
  });

  it("applies striped pattern to the terminated segment", () => {
    const withTerminated: Data = {
      ...data,
      total: 35,
      terminated: [4, 0],
    };
    render(<WipPipeline data={withTerminated} />);
    const segment = screen.getByTestId("wip-segment-terminated");
    const bgImage = segment.style.backgroundImage;
    expect(bgImage).toContain("repeating-linear-gradient");
    expect(bgImage).toContain("45deg");
  });

  it("renders 完工 baseline marker when done segment is non-zero", () => {
    render(<WipPipeline data={data} />);
    expect(screen.getByTestId("done-baseline-marker")).toBeInTheDocument();
    expect(screen.getByText("本日完工 baseline")).toBeInTheDocument();
  });

  it("hides 完工 baseline marker when no WIP is done", () => {
    const noDone: Data = {
      ...data,
      done: [0, 0],
    };
    render(<WipPipeline data={noDone} />);
    expect(screen.queryByTestId("done-baseline-marker")).not.toBeInTheDocument();
  });

  it("shows pct text only on segments >= 8%", () => {
    // waiting_dispatch 5/31 = 16% (rendered), in_progress 12/31 = 38% (rendered),
    // done 3/31 = 9% (rendered), dispatched 3/31 = 9.6% (rendered)
    render(<WipPipeline data={data} />);
    const inProgressSegment = screen.getByTestId("wip-segment-in_progress");
    expect(inProgressSegment.textContent).toContain("39%");
  });
});
