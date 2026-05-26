"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useResourceQuery } from "@/hooks/useResourceQuery";
import { errorMessage } from "@/lib/errorMessage";
import { reportsApi } from "@/services/reports-api";
import { experimentsApi } from "@/services/experiments-api";
import { MOCK_REPORTS, MOCK_WIPS } from "@/mocks/lab";
import {
  DRAFT_STATUSES,
  EXPERIMENTS_KEY,
  FORMAL_REPORT_STATUSES,
  REPORTS_KEY,
  TEMPLATES_KEY,
} from "../constants";
import type { Banner, Report, RunFn, Wip } from "../types";

/** 實驗報告頁的資料 + 狀態 + 操作邏輯（queries / 權限 / 衍生清單 / run / 範本）。 */
export function useReportPage() {
  const queryClient = useQueryClient();
  const {
    data: reports,
    loading,
    offline,
    reload,
  } = useResourceQuery<Report[]>(REPORTS_KEY, reportsApi.list, MOCK_REPORTS);
  const { data: wips } = useResourceQuery<Wip[]>(EXPERIMENTS_KEY, experimentsApi.list, MOCK_WIPS);
  const { data: templates } = useQuery({
    queryKey: TEMPLATES_KEY,
    queryFn: reportsApi.listTemplates,
  });
  const { hasPermission } = useAuth();
  const [msg, setMsg] = useState<Banner | null>(null);
  const [detail, setDetail] = useState<Report | null>(null);
  const [editing, setEditing] = useState<Report | null>(null);
  const [creating, setCreating] = useState(false);

  // 建立/編輯/送審/發布需 reports:operate；審核需 reports:review。權限來自登入者。
  const canStaff = hasPermission("reports:operate");
  const isChief = hasPermission("reports:review");

  // 已有正式報告（已確認/已發布/已回傳）的 WIP 不再列入可建立清單，避免重複開立。
  const wipsWithFormalReport = new Set(
    reports.filter((r) => FORMAL_REPORT_STATUSES.includes(r.status)).map((r) => r.wipId)
  );
  const creatable = wips.filter(
    (w) => (w.status === "待確認" || w.status === "已完成") && !wipsWithFormalReport.has(w.wipId)
  );
  const draftReports = reports.filter((r) => DRAFT_STATUSES.includes(r.status));
  const formalReports = reports.filter((r) => !DRAFT_STATUSES.includes(r.status));

  // run() 保留原本成功/失敗橫幅 UX；寫入走 service(cookie 驗證)後使快取失效。
  const run: RunFn = async (fn, okText) => {
    try {
      await fn();
      setMsg({ text: okText, ok: true });
      await queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
      reload();
    } catch (e) {
      setMsg({ text: errorMessage(e), ok: false });
    } finally {
      setEditing(null);
      setCreating(false);
    }
  };

  async function saveAsTemplate(r: Report) {
    const name = window.prompt("範本名稱（會參考此報告的委託單與內容）", r.title);
    if (!name) return;
    await run(() => reportsApi.saveTemplate({ name, fromReportId: r.reportId }), "已存成範本");
    await queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY });
  }

  const openCreate = () => {
    setCreating(true);
    setMsg(null);
  };
  const openEdit = (r: Report) => {
    setEditing(r);
    setMsg(null);
  };

  return {
    loading,
    offline,
    templates: templates ?? [],
    canStaff,
    isChief,
    creatable,
    draftReports,
    formalReports,
    msg,
    detail,
    setDetail,
    editing,
    setEditing,
    creating,
    setCreating,
    run,
    saveAsTemplate,
    openCreate,
    openEdit,
  };
}
