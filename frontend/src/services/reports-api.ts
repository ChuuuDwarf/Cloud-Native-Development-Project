import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
import type { Report, ReportTemplate } from "@/types/lab";

/** Payload for 編輯報告 (summary / conclusion / 新增附件檔名). */
export interface ReportEditPayload {
  summary?: string | null;
  conclusion?: string | null;
  attachmentName?: string | null;
}

/** 新增報告選項：自填內容、要生假數據的實驗項目、套用範本、是否直接送審。 */
export interface ReportCreatePayload {
  summary?: string | null;
  conclusion?: string | null;
  experimentItems?: string[];
  templateId?: number | null;
  submit?: boolean;
}

/** 存範本的 payload。 */
export interface ReportTemplatePayload {
  name: string;
  orderId?: string | null;
  summary?: string;
  conclusion?: string;
  fromReportId?: string | null;
}

/** Payload for 主管審核報告. */
export interface ReportReviewPayload {
  approve: boolean;
  comment?: string | null;
}

/**
 * 實驗報告 API client — wraps `/reports` (baseURL already adds `/api`).
 * Cookie auth via httpClient; the old X-Role header is dropped. The list
 * endpoint returns the standard `PageResponse` (`{ items, page, pageSize,
 * total }`); the rest return `ApiResponse<T>` (`{ data, message }`).
 */
export const reportsApi = {
  async list(): Promise<Report[]> {
    const res = await httpClient.get<PageResponse<Report>>("/reports");
    return res.data.items;
  },

  /** 從實驗結果建立報告（可自填內容、選實驗項目生假數據、套範本、直接送審）。 */
  async create(wipId: string, opts: ReportCreatePayload = {}): Promise<Report> {
    const res = await httpClient.post<ApiResponse<Report>>("/reports", {
      wipId,
      ...opts,
    });
    return res.data.data;
  },

  /** 報告範本清單。 */
  async listTemplates(): Promise<ReportTemplate[]> {
    const res =
      await httpClient.get<PageResponse<ReportTemplate>>("/reports/templates");
    return res.data.items;
  },

  /** 存報告範本（可參考委託單或由現有報告存成）。 */
  async saveTemplate(payload: ReportTemplatePayload): Promise<ReportTemplate> {
    const res = await httpClient.post<ApiResponse<ReportTemplate>>(
      "/reports/templates",
      payload,
    );
    return res.data.data;
  },

  async edit(reportId: string, payload: ReportEditPayload): Promise<Report> {
    const res = await httpClient.patch<ApiResponse<Report>>(
      `/reports/${reportId}`,
      payload,
    );
    return res.data.data;
  },

  /** 送審 (草稿/已改版 → 待審核). */
  async submit(reportId: string): Promise<Report> {
    const res = await httpClient.post<ApiResponse<Report>>(
      `/reports/${reportId}/submit`,
    );
    return res.data.data;
  },

  /** 主管審核 (確認 / 退回). */
  async review(
    reportId: string,
    payload: ReportReviewPayload,
  ): Promise<Report> {
    const res = await httpClient.post<ApiResponse<Report>>(
      `/reports/${reportId}/review`,
      payload,
    );
    return res.data.data;
  },

  /** 發布並回傳使用者 (已確認 → 已發布/已回傳). */
  async publish(reportId: string): Promise<Report> {
    const res = await httpClient.post<ApiResponse<Report>>(
      `/reports/${reportId}/publish`,
    );
    return res.data.data;
  },
};
