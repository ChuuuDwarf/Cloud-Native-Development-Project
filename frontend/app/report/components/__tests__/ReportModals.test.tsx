import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Report, ReportTemplate, Wip } from "@/types/lab";

const { createMock, editMock } = vi.hoisted(() => ({
  createMock: vi.fn(),
  editMock: vi.fn(),
}));

vi.mock("@/services/reports-api", () => ({
  reportsApi: {
    create: createMock,
    edit: editMock,
  },
}));

import CreateModal from "../CreateModal";
import EditModal from "../EditModal";

const wips: Wip[] = [
  {
    wipId: "WIP-1",
    orderId: "O-1",
    sample: "Sample A",
    experimentItem: "SEM",
    machineId: null,
    recipe: null,
    status: "待確認",
    progress: 100,
    operator: null,
    checkInAt: null,
    checkOutAt: null,
    resultNote: null,
    rawDataUrl: null,
    dataVerified: true,
    abort: null,
    history: [],
  },
  {
    wipId: "WIP-2",
    orderId: "O-2",
    sample: "Sample B",
    experimentItem: "IV",
    machineId: null,
    recipe: null,
    status: "已完成",
    progress: 100,
    operator: null,
    checkInAt: null,
    checkOutAt: null,
    resultNote: null,
    rawDataUrl: null,
    dataVerified: true,
    abort: null,
    history: [],
  },
];

const templates: ReportTemplate[] = [
  {
    id: 7,
    name: "可靠度範本",
    orderId: "O-7",
    summary: "template summary",
    conclusion: "template conclusion",
    createdBy: "Lead",
    createdAt: "2026-01-01",
  },
];

const report: Report = {
  reportId: "R-1",
  orderId: "O-1",
  wipId: "WIP-1",
  title: "材料分析報告",
  summary: "原摘要",
  conclusion: "原結論",
  attachments: [],
  status: "草稿",
  createdAt: "2026-01-01",
  createdBy: "Alice",
  versions: [{ version: 1, status: "草稿", at: "2026-01-01", by: "Alice", note: "created" }],
};

function runAndInvoke() {
  return vi.fn(async (fn: () => Promise<unknown>) => {
    await fn();
  });
}

describe("CreateModal", () => {
  beforeEach(() => {
    createMock.mockReset();
    editMock.mockReset();
  });

  it("shows the empty message and disables submit buttons without WIPs", () => {
    render(<CreateModal wips={[]} templates={[]} run={vi.fn()} onClose={vi.fn()} />);

    expect(screen.getByText("目前沒有「待確認 / 已完成」的實驗可建立報告。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "建立草稿" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "建立並送審" })).toBeDisabled();
  });

  it("creates a draft with selected WIP, template, summary, conclusion, and checked items", async () => {
    createMock.mockResolvedValue({ reportId: "R-new" });
    const run = runAndInvoke();
    render(<CreateModal wips={wips} templates={templates} run={run} onClose={vi.fn()} />);

    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "WIP-2" } });
    fireEvent.change(selects[1], { target: { value: "7" } });
    fireEvent.change(screen.getByPlaceholderText(/自動帶入機台/), {
      target: { value: "手動摘要" },
    });
    fireEvent.change(screen.getAllByRole("textbox")[1], { target: { value: "手動結論" } });
    fireEvent.click(screen.getByLabelText("SEM"));

    fireEvent.click(screen.getByRole("button", { name: "建立草稿" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith("WIP-2", {
        summary: "手動摘要",
        conclusion: "手動結論",
        experimentItems: ["IV", "SEM"],
        templateId: 7,
        submit: false,
      });
    });
    expect(run).toHaveBeenCalledWith(expect.any(Function), "已建立報告草稿");
  });

  it("sends null and undefined defaults when creating and submitting an empty report", async () => {
    createMock.mockResolvedValue({ reportId: "R-new" });
    const run = runAndInvoke();
    render(<CreateModal wips={wips} templates={[]} run={run} onClose={vi.fn()} />);

    fireEvent.click(screen.getByLabelText("SEM"));
    fireEvent.click(screen.getByRole("button", { name: "建立並送審" }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith("WIP-1", {
        summary: null,
        conclusion: null,
        experimentItems: undefined,
        templateId: null,
        submit: true,
      });
    });
    expect(run).toHaveBeenCalledWith(expect.any(Function), "已建立並送審");
  });
});

describe("EditModal", () => {
  beforeEach(() => {
    createMock.mockReset();
    editMock.mockReset();
  });

  it("edits summary, conclusion, and attachment name", async () => {
    editMock.mockResolvedValue({ reportId: "R-1" });
    const run = runAndInvoke();
    render(<EditModal r={report} run={run} onClose={vi.fn()} />);

    const textboxes = screen.getAllByRole("textbox");
    fireEvent.change(textboxes[0], { target: { value: "新摘要" } });
    fireEvent.change(textboxes[1], { target: { value: "新結論" } });
    fireEvent.change(textboxes[2], { target: { value: "report.pdf" } });
    fireEvent.click(screen.getByRole("button", { name: "儲存" }));

    await waitFor(() => {
      expect(editMock).toHaveBeenCalledWith("R-1", {
        summary: "新摘要",
        conclusion: "新結論",
        attachmentName: "report.pdf",
      });
    });
    expect(run).toHaveBeenCalledWith(expect.any(Function), "報告已更新");
  });

  it("sends null when attachment name is empty", async () => {
    editMock.mockResolvedValue({ reportId: "R-1" });
    render(<EditModal r={report} run={runAndInvoke()} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "儲存" }));

    await waitFor(() => {
      expect(editMock).toHaveBeenCalledWith("R-1", {
        summary: "原摘要",
        conclusion: "原結論",
        attachmentName: null,
      });
    });
  });
});
