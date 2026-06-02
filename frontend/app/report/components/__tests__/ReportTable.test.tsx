import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Report } from "@/types/lab";

const { submitMock, reviewMock, publishMock } = vi.hoisted(() => ({
  submitMock: vi.fn(),
  reviewMock: vi.fn(),
  publishMock: vi.fn(),
}));

vi.mock("@/services/reports-api", () => ({
  reportsApi: {
    submit: submitMock,
    review: reviewMock,
    publish: publishMock,
  },
}));

import ReportTable from "../ReportTable";

const baseReport: Report = {
  reportId: "R-1",
  orderId: "O-1",
  wipId: "WIP-1",
  title: "材料分析報告",
  summary: "summary",
  conclusion: "conclusion",
  attachments: [],
  status: "草稿",
  createdAt: "2026-01-01T00:00:00Z",
  createdBy: "Alice",
  versions: [{ version: 1, status: "草稿", at: "2026-01-01", by: "Alice", note: "created" }],
};

function report(status: string, id = `R-${status}`): Report {
  return { ...baseReport, reportId: id, status };
}

function setup(overrides: Partial<Parameters<typeof ReportTable>[0]> = {}) {
  const props = {
    rows: [baseReport],
    loading: false,
    emptyText: "沒有報告",
    canStaff: true,
    isChief: false,
    offline: false,
    onEdit: vi.fn(),
    onDetail: vi.fn(),
    run: vi.fn(async (fn: () => Promise<unknown>) => {
      await fn();
    }),
    ...overrides,
  };

  render(<ReportTable {...props} />);
  return props;
}

describe("ReportTable", () => {
  beforeEach(() => {
    submitMock.mockReset();
    reviewMock.mockReset();
    publishMock.mockReset();
  });

  it("renders loading and empty states through DataState", () => {
    const { rerender } = render(
      <ReportTable
        rows={[]}
        loading
        emptyText="沒有報告"
        canStaff
        isChief={false}
        offline={false}
        onEdit={vi.fn()}
        onDetail={vi.fn()}
        run={vi.fn()}
      />
    );

    expect(screen.getByText("載入中…")).toBeInTheDocument();

    rerender(
      <ReportTable
        rows={[]}
        loading={false}
        emptyText="沒有報告"
        canStaff
        isChief={false}
        offline={false}
        onEdit={vi.fn()}
        onDetail={vi.fn()}
        run={vi.fn()}
      />
    );

    expect(screen.getByText("沒有報告")).toBeInTheDocument();
  });

  it("opens detail when clicking the report id", () => {
    const props = setup();

    fireEvent.click(screen.getByRole("button", { name: "R-1" }));

    expect(props.onDetail).toHaveBeenCalledWith(baseReport);
  });

  it("lets staff edit and submit draft reports", async () => {
    submitMock.mockResolvedValue(report("待審核"));
    const props = setup({ rows: [report("草稿", "R-draft")] });

    fireEvent.click(screen.getByRole("button", { name: "編輯" }));
    fireEvent.click(screen.getByRole("button", { name: "送審" }));

    expect(props.onEdit).toHaveBeenCalledWith(expect.objectContaining({ reportId: "R-draft" }));
    expect(props.run).toHaveBeenCalledWith(expect.any(Function), "已提交審核");
    expect(submitMock).toHaveBeenCalledWith("R-draft");
  });

  it("lets chiefs reject or approve pending reports", async () => {
    reviewMock.mockResolvedValue(report("已確認"));
    const props = setup({ rows: [report("待審核", "R-review")], canStaff: false, isChief: true });

    fireEvent.click(screen.getByRole("button", { name: "退回" }));
    fireEvent.click(screen.getByRole("button", { name: "確認" }));

    expect(props.run).toHaveBeenNthCalledWith(1, expect.any(Function), "報告已退回");
    expect(props.run).toHaveBeenNthCalledWith(2, expect.any(Function), "報告已確認");
    expect(reviewMock).toHaveBeenNthCalledWith(1, "R-review", { approve: false });
    expect(reviewMock).toHaveBeenNthCalledWith(2, "R-review", { approve: true });
  });

  it("lets staff publish confirmed reports", () => {
    publishMock.mockResolvedValue(report("已發布"));
    const props = setup({ rows: [report("已確認", "R-confirmed")] });

    fireEvent.click(screen.getByRole("button", { name: "發布回傳" }));

    expect(props.run).toHaveBeenCalledWith(expect.any(Function), "報告已發布並回傳");
    expect(publishMock).toHaveBeenCalledWith("R-confirmed");
  });

  it("lets users view published reports and disables offline actions", () => {
    const props = setup({
      rows: [report("已發布", "R-pub"), report("草稿", "R-offline")],
      offline: true,
    });

    fireEvent.click(screen.getByRole("button", { name: "查閱 / 下載" }));

    expect(props.onDetail).toHaveBeenCalledWith(expect.objectContaining({ reportId: "R-pub" }));
    expect(within(screen.getByText("R-offline").closest("tr")!).getByText("編輯")).toBeDisabled();
    expect(within(screen.getByText("R-offline").closest("tr")!).getByText("送審")).toBeDisabled();
  });

  it("shows a dash when no action applies", () => {
    setup({ rows: [report("待審核", "R-no-action")], canStaff: false, isChief: false });

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
