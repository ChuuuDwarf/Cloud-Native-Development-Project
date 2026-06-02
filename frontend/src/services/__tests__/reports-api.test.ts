import { beforeEach, describe, expect, it, vi } from "vitest";

const { getMock, postMock, patchMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
}));

vi.mock("@/api/httpClient", () => ({
  httpClient: {
    get: getMock,
    post: postMock,
    patch: patchMock,
  },
}));

import { reportsApi } from "@/services/reports-api";

describe("reportsApi", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  it("list() GETs /reports and returns page items", async () => {
    const reports = [{ reportId: "R-1" }];
    getMock.mockResolvedValue({ data: { items: reports } });

    await expect(reportsApi.list()).resolves.toEqual(reports);

    expect(getMock).toHaveBeenCalledWith("/reports");
  });

  it("create() POSTs wipId with options and unwraps data", async () => {
    const report = { reportId: "R-2" };
    const opts = { summary: "s", conclusion: "c", submit: true };
    postMock.mockResolvedValue({ data: { data: report } });

    await expect(reportsApi.create("WIP-1", opts)).resolves.toEqual(report);

    expect(postMock).toHaveBeenCalledWith("/reports", { wipId: "WIP-1", ...opts });
  });

  it("listTemplates() GETs /reports/templates and returns page items", async () => {
    const templates = [{ id: 1, name: "T" }];
    getMock.mockResolvedValue({ data: { items: templates } });

    await expect(reportsApi.listTemplates()).resolves.toEqual(templates);

    expect(getMock).toHaveBeenCalledWith("/reports/templates");
  });

  it("saveTemplate() POSTs the template payload and unwraps data", async () => {
    const payload = { name: "T", orderId: "O-1", summary: "s", conclusion: "c" };
    const template = { id: 1, ...payload };
    postMock.mockResolvedValue({ data: { data: template } });

    await expect(reportsApi.saveTemplate(payload)).resolves.toEqual(template);

    expect(postMock).toHaveBeenCalledWith("/reports/templates", payload);
  });

  it("edit() PATCHes a report and unwraps data", async () => {
    const payload = { summary: "new", conclusion: null, attachmentName: "report.pdf" };
    const report = { reportId: "R-3" };
    patchMock.mockResolvedValue({ data: { data: report } });

    await expect(reportsApi.edit("R-3", payload)).resolves.toEqual(report);

    expect(patchMock).toHaveBeenCalledWith("/reports/R-3", payload);
  });

  it("submit(), review(), and publish() POST action endpoints", async () => {
    const report = { reportId: "R-4" };
    postMock.mockResolvedValue({ data: { data: report } });

    await expect(reportsApi.submit("R-4")).resolves.toEqual(report);
    await expect(reportsApi.review("R-4", { approve: false, comment: "fix" })).resolves.toEqual(
      report
    );
    await expect(reportsApi.publish("R-4")).resolves.toEqual(report);

    expect(postMock).toHaveBeenNthCalledWith(1, "/reports/R-4/submit");
    expect(postMock).toHaveBeenNthCalledWith(2, "/reports/R-4/review", {
      approve: false,
      comment: "fix",
    });
    expect(postMock).toHaveBeenNthCalledWith(3, "/reports/R-4/publish");
  });
});
