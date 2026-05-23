import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import Chip from "@/components/ui/Chip";
import KpiCard from "@/components/ui/KpiCard";

describe("Chip", () => {
  it("renders the label and status dot styles", () => {
    const html = renderToStaticMarkup(<Chip type="running" label="使用中" />);

    expect(html).toContain("使用中");
    expect(html).toContain("#39d0d8");
    expect(html).toContain("inline-flex");
  });

  it("renders rejected chips with the danger color", () => {
    const html = renderToStaticMarkup(<Chip type="rejected" label="故障中" />);

    expect(html).toContain("故障中");
    expect(html).toContain("#ff4444");
  });
});

describe("KpiCard", () => {
  it("renders label, value, sub text, icon, and accent color", () => {
    const html = renderToStaticMarkup(
      <KpiCard
        label="平均稼動率"
        value="48%"
        sub="4 台機台"
        color="var(--green)"
        icon="UP"
      />,
    );

    expect(html).toContain("平均稼動率");
    expect(html).toContain("48%");
    expect(html).toContain("4 台機台");
    expect(html).toContain("UP");
    expect(html).toContain("var(--green)");
  });

  it("omits optional sub text and icon when not provided", () => {
    const html = renderToStaticMarkup(
      <KpiCard label="待派工 WIP" value={3} color="var(--blue)" />,
    );

    expect(html).toContain("待派工 WIP");
    expect(html).toContain(">3<");
    expect(html).not.toContain("undefined");
  });
});
