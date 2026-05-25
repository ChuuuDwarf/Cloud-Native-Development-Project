import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import KpiCard from "./KpiCard";

describe("KpiCard", () => {
  it("會渲染標題、數值、副標題與 icon", () => {
    const html = renderToStaticMarkup(
      <KpiCard label="待收樣" value={12} sub="今日新增 3 筆" color="#388bfd" icon="📦" />
    );

    expect(html).toContain("待收樣");
    expect(html).toContain("12");
    expect(html).toContain("今日新增 3 筆");
    expect(html).toContain("📦");
    expect(html).toContain("#388bfd");
  });

  it("沒有 sub 與 icon 時仍可正常渲染", () => {
    const html = renderToStaticMarkup(<KpiCard label="完成率" value="98%" color="#3fb950" />);

    expect(html).toContain("完成率");
    expect(html).toContain("98%");
    expect(html).toContain("#3fb950");
    expect(html).not.toContain("今日新增");
  });
});
