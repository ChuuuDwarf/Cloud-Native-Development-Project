import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Chip from "@/components/ui/Chip";

const allTypes = [
  "draft",
  "pending",
  "review",
  "approved",
  "running",
  "done",
  "rejected",
  "paused",
  "idle",
] as const;

describe("Chip", () => {
  it("renders the supplied label", () => {
    render(<Chip type="draft" label="草稿" />);
    expect(screen.getByText("草稿")).toBeInTheDocument();
  });

  it.each(allTypes)("renders without crashing for type=%s", (type) => {
    render(<Chip type={type} label={type} />);
    expect(screen.getByText(type)).toBeInTheDocument();
  });
});
