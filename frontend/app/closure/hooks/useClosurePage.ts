"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useResourceQuery } from "@/hooks/useResourceQuery";
import { errorMessage } from "@/lib/errorMessage";
import { closuresApi } from "@/services/closures-api";
import { MOCK_CLOSURES } from "@/mocks/lab";
import { CLOSURES_KEY } from "../constants";
import type { Banner, ClosureCheck } from "../types";

/** 結單頁的資料 + 狀態 + 操作邏輯（query / 權限 / run 提示）。 */
export function useClosurePage() {
  const queryClient = useQueryClient();
  const {
    data: rows,
    loading,
    offline,
    reload,
  } = useResourceQuery<ClosureCheck[]>(CLOSURES_KEY, closuresApi.list, MOCK_CLOSURES);
  const { hasPermission } = useAuth();
  const [msg, setMsg] = useState<Banner | null>(null);
  const [detail, setDetail] = useState<ClosureCheck | null>(null);
  // 轉待取件 / 取件結案需 closures:operate（人員/主管/管理者皆可,僅廠區不可）。
  const canOperate = hasPermission("closures:operate");

  // run() 保留原本成功/失敗橫幅 UX；寫入走 service(cookie 驗證)後使快取失效。
  async function run(fn: () => Promise<unknown>, okText: string) {
    try {
      await fn();
      setMsg({ text: okText, ok: true });
      await queryClient.invalidateQueries({ queryKey: CLOSURES_KEY });
      reload();
    } catch (e) {
      setMsg({ text: errorMessage(e), ok: false });
    }
  }

  return { rows, loading, offline, canOperate, msg, detail, setDetail, run };
}
