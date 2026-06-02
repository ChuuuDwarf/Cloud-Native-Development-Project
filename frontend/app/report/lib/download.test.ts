import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Report } from "../types";
import { downloadReport } from "./download";

function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    reportId: "RPT-1",
    orderId: "ORD-1",
    wipId: "WIP-1",
    title: "標題",
    summary: "摘要內容",
    conclusion: "結論內容",
    attachments: [{ name: "fig1.png", at: "2026-01-01" }],
    status: "approved",
    experimentData: { "SEM 觀察": { 倍率: "10000x", 結果: "良好" } },
    createdAt: "2026-01-01",
    createdBy: "王小明",
    versions: [{ version: 1, status: "draft", at: "2026-01-01", by: "王小明", note: "初版" }],
    ...overrides,
  };
}

describe("report/lib/download", () => {
  let createSpy: ReturnType<typeof vi.fn>;
  let revokeSpy: ReturnType<typeof vi.fn>;
  let clickSpy: ReturnType<typeof vi.fn>;
  let captured: { blob?: Blob; href?: string; download?: string } = {};

  beforeEach(() => {
    captured = {};
    createSpy = vi.fn((blob: Blob) => {
      captured.blob = blob;
      return "blob:fake-url";
    });
    revokeSpy = vi.fn();
    clickSpy = vi.fn();

    vi.stubGlobal("URL", {
      createObjectURL: createSpy,
      revokeObjectURL: revokeSpy,
    });

    vi.spyOn(document, "createElement").mockImplementation(() => {
      const anchor = {
        set href(v: string) {
          captured.href = v;
        },
        set download(v: string) {
          captured.download = v;
        },
        click: clickSpy,
      };
      return anchor as unknown as HTMLAnchorElement;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("creates a markdown blob, triggers a download, and revokes the URL", () => {
    downloadReport(makeReport());

    expect(createSpy).toHaveBeenCalledOnce();
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake-url");
    expect(captured.href).toBe("blob:fake-url");
    expect(captured.download).toBe("RPT-1.md");
    expect(captured.blob?.type).toContain("text/markdown");
  });

  it("includes report fields and experiment data in the markdown body", async () => {
    downloadReport(makeReport());
    const text = await captured.blob?.text();
    expect(text).toContain("# 實驗報告 RPT-1");
    expect(text).toContain("摘要內容");
    expect(text).toContain("結論內容");
    expect(text).toContain("### SEM 觀察");
    expect(text).toContain("- 倍率：10000x");
    expect(text).toContain("- fig1.png");
    expect(text).toContain("v1 · draft · 初版");
  });

  it("renders em-dash placeholders for empty optional sections", async () => {
    downloadReport(
      makeReport({ summary: "", conclusion: "", attachments: [], experimentData: undefined })
    );
    const text = (await captured.blob?.text()) ?? "";
    // summary, conclusion, attachments all fall back to "—"
    const dashCount = (text.match(/—/g) ?? []).length;
    expect(dashCount).toBeGreaterThanOrEqual(3);
  });

  it("omits the version note separator when note is empty", async () => {
    downloadReport(
      makeReport({
        versions: [{ version: 2, status: "approved", at: "2026-02-01", by: "李四", note: "" }],
      })
    );
    const text = (await captured.blob?.text()) ?? "";
    expect(text).toContain("v2 · approved（2026-02-01 · 李四）");
  });
});
