import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CompletionsList from "../CompletionsList";
import type { CompletionRow } from "@/types/dashboard";

const rows: CompletionRow[] = [
  {
    wip_no: "WIP-A001",
    order_no: "ORD-2025-0012",
    lab_name: "LAB-A",
    returned_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
];

describe("CompletionsList", () => {
  it("renders rows", () => {
    render(<CompletionsList rows={rows} />);
    expect(screen.getByText("WIP-A001")).toBeInTheDocument();
    expect(screen.getByText("ORD-2025-0012")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<CompletionsList rows={[]} />);
    expect(screen.getByText("近 30 分鐘無回傳")).toBeInTheDocument();
  });
});
