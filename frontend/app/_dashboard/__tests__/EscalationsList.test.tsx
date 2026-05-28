import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import EscalationsList from "../EscalationsList";
import type { EscalationRow } from "@/types/dashboard";

const rows: EscalationRow[] = [
  {
    issue_id: "iss-1",
    lab_name: "LAB-A",
    severity: "critical",
    escalation_level: 2,
    title: "真空泵故障",
    escalated_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
  },
];

describe("EscalationsList", () => {
  it("renders rows", () => {
    render(<EscalationsList rows={rows} />);
    expect(screen.getByText("真空泵故障")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("L2")).toBeInTheDocument();
    expect(screen.getByText("LAB-A")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<EscalationsList rows={[]} />);
    expect(screen.getByText("過去 24h 無升級")).toBeInTheDocument();
  });
});
