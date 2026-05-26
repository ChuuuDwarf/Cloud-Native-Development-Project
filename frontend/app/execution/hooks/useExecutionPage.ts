"use client";
import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useResourceQuery } from "@/hooks/useResourceQuery";
import { errorMessage } from "@/lib/errorMessage";
import { experimentsApi } from "@/services/experiments-api";
import { machinesApi } from "@/services/machines-api";
import { recipesApi } from "@/services/recipes-api";
import { MOCK_WIPS } from "@/mocks/lab";
import type { Wip } from "@/types/lab";
import { EXPERIMENTS_KEY } from "../constants";
import type { Banner, ModalKind, RunFn } from "../types";

/** 實驗執行頁的資料 + 狀態 + 操作邏輯（query / 權限 / KPI / run / modal）。 */
export function useExecutionPage() {
  const queryClient = useQueryClient();
  const {
    data: wips,
    loading,
    offline,
    reload,
  } = useResourceQuery<Wip[]>(EXPERIMENTS_KEY, experimentsApi.list, MOCK_WIPS, {
    // 每 3 秒輪詢，讓背景自動推進的進度即時反映在進度條上。
    refetchInterval: 3000,
  });
  const machinesQuery = useQuery({ queryKey: ["machines"], queryFn: machinesApi.list });
  const recipesQuery = useQuery({ queryKey: ["recipes"], queryFn: recipesApi.list });
  const { hasPermission } = useAuth();
  const [modal, setModal] = useState<ModalKind>(null);
  const [target, setTarget] = useState<Wip | null>(null);
  const [msg, setMsg] = useState<Banner | null>(null);

  // 操作（上機/下機/進度/結果/確認/中止申請）需 experiments:operate；
  // 審核中止需 experiments:review。權限來自登入者（cookie 驗證）。
  const canOperate = hasPermission("experiments:operate");
  const isChief = hasPermission("experiments:review");

  const kpi = useMemo(() => {
    const c = (s: string) => wips.filter((w) => w.status === s).length;
    return {
      checkin: c("待上機"),
      running: c("執行中"),
      out: c("已下機"),
      confirm: c("待確認"),
      done: c("已完成"),
    };
  }, [wips]);

  // 視窗不管成功或失敗都關閉；結果顯示在上方提醒（提醒不自動消失）。
  const run: RunFn = async (fn, okText) => {
    try {
      await fn();
      setMsg({ text: okText, ok: true });
      await queryClient.invalidateQueries({ queryKey: EXPERIMENTS_KEY });
      reload();
    } catch (e) {
      setMsg({ text: errorMessage(e), ok: false });
    } finally {
      setModal(null);
    }
  };

  const open = (kind: ModalKind, w: Wip) => {
    setTarget(w);
    setModal(kind);
    setMsg(null);
  };
  const closeModal = () => setModal(null);
  const flashError = (text: string) => setMsg({ text, ok: false });

  return {
    wips,
    loading,
    offline,
    kpi,
    canOperate,
    isChief,
    modal,
    target,
    machines: machinesQuery.data ?? [],
    recipes: recipesQuery.data ?? [],
    msg,
    run,
    open,
    closeModal,
    flashError,
  };
}
