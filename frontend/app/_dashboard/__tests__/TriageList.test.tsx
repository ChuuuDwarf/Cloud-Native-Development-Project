import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import TriageList from "../TriageList";
import type { TriageItem } from "@/types/dashboard";

const items: TriageItem[] = [
  {
    type: "pending_approval",
    ref_id: "ORD-001",
    label: "ORD-001 · 張工",
    lab_name: null,
    severity: null,
    created_at: new Date(Date.now() - 7 * 60 * 1000).toISOString(),
  },
  {
    type: "escalated_issue",
    ref_id: "ISS-091",
    label: "真空泵故障",
    lab_name: "LAB-A",
    severity: "critical",
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
  },
];

describe("TriageList", () => {
  it("renders list with both items", () => {
    render(<TriageList items={items} />);
    expect(screen.getByText("ORD-001 · 張工")).toBeInTheDocument();
    expect(screen.getByText("真空泵故障")).toBeInTheDocument();
  });

  it("shows severity for issue items", () => {
    render(<TriageList items={items} />);
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<TriageList items={[]} />);
    expect(screen.getByText("目前無待處理事項")).toBeInTheDocument();
  });
});
