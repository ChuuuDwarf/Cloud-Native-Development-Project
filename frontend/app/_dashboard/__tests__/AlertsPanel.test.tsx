import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AlertsPanel from "../AlertsPanel";
import type { EscalationRow, TriageItem } from "@/types/dashboard";

const minutesAgo = (m: number) => new Date(Date.now() - m * 60 * 1000).toISOString();

describe("AlertsPanel", () => {
  it("renders empty state when both lists are empty", () => {
    render(<AlertsPanel unackHighCriticalIssues={[]} recentEscalations={[]} />);
    expect(screen.getByText("目前無未處理異常")).toBeInTheDocument();
    expect(screen.queryByTestId("alerts-panel-row")).not.toBeInTheDocument();
  });

  it("renders rows from both input lists", () => {
    const unack: TriageItem[] = [
      {
        type: "open_issue",
        ref_id: "ISS-100",
        label: "樣品損毀",
        lab_name: "LAB-B",
        severity: "high",
        created_at: minutesAgo(30),
      },
    ];
    const escalations: EscalationRow[] = [
      {
        issue_id: "ISS-200",
        lab_name: "LAB-C",
        severity: "high",
        escalation_level: 1,
        title: "機台保養",
        escalated_at: minutesAgo(120),
      },
    ];

    render(<AlertsPanel unackHighCriticalIssues={unack} recentEscalations={escalations} />);
    expect(screen.getByText("樣品損毀")).toBeInTheDocument();
    expect(screen.getByText(/機台保養/)).toBeInTheDocument();
    expect(screen.getAllByTestId("alerts-panel-row")).toHaveLength(2);
  });

  it("sorts unack-escalated > unack-critical > unack-high > ack'd escalations", () => {
    const unack: TriageItem[] = [
      // unack high (group 2)
      {
        type: "open_issue",
        ref_id: "ISS-HIGH",
        label: "high item",
        lab_name: "LAB-A",
        severity: "high",
        created_at: minutesAgo(5),
      },
      // unack critical (group 1)
      {
        type: "open_issue",
        ref_id: "ISS-CRIT",
        label: "critical item",
        lab_name: "LAB-A",
        severity: "critical",
        created_at: minutesAgo(50),
      },
      // unack escalated (group 0)
      {
        type: "escalated_issue",
        ref_id: "ISS-ESC",
        label: "escalated item",
        lab_name: "LAB-A",
        severity: "critical",
        created_at: minutesAgo(60),
      },
    ];
    const escalations: EscalationRow[] = [
      // ack'd, not in unack list (group 3)
      {
        issue_id: "ISS-ACK",
        lab_name: "LAB-Z",
        severity: "critical",
        escalation_level: 2,
        title: "ack'd item",
        escalated_at: minutesAgo(15),
      },
      // also include the escalated unack row so it gets escalation_level
      {
        issue_id: "ISS-ESC",
        lab_name: "LAB-A",
        severity: "critical",
        escalation_level: 2,
        title: "escalated item",
        escalated_at: minutesAgo(60),
      },
    ];

    render(<AlertsPanel unackHighCriticalIssues={unack} recentEscalations={escalations} />);
    const rows = screen.getAllByTestId("alerts-panel-row");
    const ids = rows.map((r) => r.getAttribute("data-issue-id"));
    expect(ids).toEqual(["ISS-ESC", "ISS-CRIT", "ISS-HIGH", "ISS-ACK"]);
  });

  it("dedupes by issue_id: items in both lists appear once", () => {
    const unack: TriageItem[] = [
      {
        type: "open_issue",
        ref_id: "ISS-DUP",
        label: "duplicate item",
        lab_name: "LAB-A",
        severity: "critical",
        created_at: minutesAgo(10),
      },
    ];
    const escalations: EscalationRow[] = [
      {
        issue_id: "ISS-DUP",
        lab_name: "LAB-A",
        severity: "critical",
        escalation_level: 1,
        title: "duplicate item",
        escalated_at: minutesAgo(10),
      },
    ];

    render(<AlertsPanel unackHighCriticalIssues={unack} recentEscalations={escalations} />);
    const rows = screen.getAllByTestId("alerts-panel-row");
    expect(rows).toHaveLength(1);
    expect(rows[0].getAttribute("data-acknowledged")).toBe("false");
  });

  it("ack'd rows have reduced opacity", () => {
    const escalations: EscalationRow[] = [
      {
        issue_id: "ISS-ACK",
        lab_name: "LAB-A",
        severity: "high",
        escalation_level: 1,
        title: "ack'd",
        escalated_at: minutesAgo(20),
      },
    ];

    render(<AlertsPanel unackHighCriticalIssues={[]} recentEscalations={escalations} />);
    const row = screen.getByTestId("alerts-panel-row");
    expect(row.getAttribute("data-acknowledged")).toBe("true");
    expect(row.style.opacity).toBe("0.55");
    expect(within(row).getByText("(ack)")).toBeInTheDocument();
  });

  it("shows escalation level badge only when escalation_level > 0", () => {
    const unack: TriageItem[] = [
      {
        type: "open_issue",
        ref_id: "ISS-PLAIN",
        label: "plain high",
        lab_name: "LAB-A",
        severity: "high",
        created_at: minutesAgo(5),
      },
    ];
    const escalations: EscalationRow[] = [
      {
        issue_id: "ISS-L2",
        lab_name: "LAB-B",
        severity: "critical",
        escalation_level: 2,
        title: "level 2 ack",
        escalated_at: minutesAgo(30),
      },
    ];

    render(<AlertsPanel unackHighCriticalIssues={unack} recentEscalations={escalations} />);
    expect(screen.getByText("L2")).toBeInTheDocument();
    expect(screen.queryByText("L0")).not.toBeInTheDocument();
  });

  it("caps rendered rows at 7", () => {
    const unack: TriageItem[] = Array.from({ length: 10 }, (_, i) => ({
      type: "open_issue" as const,
      ref_id: `ISS-${i}`,
      label: `item ${i}`,
      lab_name: "LAB-A",
      severity: "high" as const,
      created_at: minutesAgo(i),
    }));

    render(<AlertsPanel unackHighCriticalIssues={unack} recentEscalations={[]} />);
    expect(screen.getAllByTestId("alerts-panel-row")).toHaveLength(7);
  });
});
