import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ThroughputChart from "../ThroughputChart";
import type { ThroughputPoint } from "@/types/dashboard";

function makeData(spec: Partial<Record<number, [number, number]>>): ThroughputPoint[] {
  return Array.from({ length: 24 }, (_, i) => {
    const [c, r] = spec[i] ?? [0, 0];
    return { hour_offset: i, completed: c, returned: r };
  });
}

describe("ThroughputChart", () => {
  it("renders header with 24h totals", () => {
    const data = makeData({ 5: [3, 1], 10: [4, 2], 20: [5, 3] });
    render(<ThroughputChart data={data} />);
    expect(screen.getByText("24h 產出趨勢")).toBeInTheDocument();
    const totals = screen.getByTestId("throughput-totals");
    expect(totals.textContent).toContain("完工 12");
    expect(totals.textContent).toContain("回傳 6");
  });

  it("renders the LineChart when at least one bucket is non-zero", () => {
    const data = makeData({ 12: [1, 0] });
    render(<ThroughputChart data={data} />);
    expect(screen.queryByTestId("throughput-empty")).not.toBeInTheDocument();
  });

  it("shows the empty state when data is empty", () => {
    render(<ThroughputChart data={[]} />);
    expect(screen.getByTestId("throughput-empty")).toBeInTheDocument();
    expect(screen.getByText("近 24h 無產出")).toBeInTheDocument();
  });

  it("shows the empty state when all buckets are zero", () => {
    render(<ThroughputChart data={makeData({})} />);
    expect(screen.getByTestId("throughput-empty")).toBeInTheDocument();
  });

  it("totals stay at 0 when data is empty", () => {
    render(<ThroughputChart data={[]} />);
    const totals = screen.getByTestId("throughput-totals");
    expect(totals.textContent).toContain("完工 0");
    expect(totals.textContent).toContain("回傳 0");
  });
});
