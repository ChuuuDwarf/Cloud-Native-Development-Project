import { render, screen } from "@testing-library/react";
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
});
