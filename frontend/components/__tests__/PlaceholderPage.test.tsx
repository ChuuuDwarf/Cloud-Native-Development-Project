import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PlaceholderPage from "@/components/PlaceholderPage";

describe("PlaceholderPage", () => {
  it("renders title, subtitle and the construction message", () => {
    render(<PlaceholderPage title="標題" subtitle="SUB · TITLE" />);
    expect(screen.getByText("標題")).toBeInTheDocument();
    expect(screen.getByText("SUB · TITLE")).toBeInTheDocument();
    expect(screen.getByText("頁面施工中")).toBeInTheDocument();
  });

  it("renders the API hint when apiPath is supplied", () => {
    render(
      <PlaceholderPage title="T" subtitle="S" apiPath="GET /api/orders" />,
    );
    expect(screen.getByText(/GET \/api\/orders/)).toBeInTheDocument();
  });

  it("omits the API hint when apiPath is not supplied", () => {
    render(<PlaceholderPage title="T" subtitle="S" />);
    expect(screen.queryByText(/API：/)).not.toBeInTheDocument();
  });
});
