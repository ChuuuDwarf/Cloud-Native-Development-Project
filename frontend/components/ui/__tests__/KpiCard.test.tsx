import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import KpiCard from "@/components/ui/KpiCard";

describe("KpiCard", () => {
  it("renders label, value and optional sub + icon", () => {
    render(<KpiCard label="OPEN ORDERS" value={42} sub="vs last week" color="#388bfd" icon="📋" />);
    expect(screen.getByText("OPEN ORDERS")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("vs last week")).toBeInTheDocument();
    expect(screen.getByText("📋")).toBeInTheDocument();
  });

  it("renders without sub/icon when omitted", () => {
    render(<KpiCard label="A" value="100" color="#3fb950" />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
  });
});
