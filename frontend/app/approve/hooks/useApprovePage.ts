"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { userApi } from "@/services/user-api";
import type { MasterData } from "@/services/master-data-api";
import type {
  ModalState,
  Order,
  OrderAction,
  OrderHistory,
  OrderItem,
  OrderStatus,
  ReasonModalState,
} from "../types";
import { requestJson } from "../lib/api";
import { actionLabel, statusLabel } from "../lib/labels";
import { sortApprovalOrders } from "../lib/approvalRules";

const emptyMasterData: Pick<MasterData, "departments" | "labs" | "experiments"> = {
  departments: [],
  labs: [],
  experiments: [],
};

export function useApprovePage() {
  const { user, hasPermission } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [quotaOverride, setQuotaOverride] = useState(false);
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState("尚未執行任何動作");
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [reasonModal, setReasonModal] = useState<ReasonModalState>({ open: false });
  const [masterData, setMasterData] = useState(emptyMasterData);
  const [usersById, setUsersById] = useState<Record<string, string | undefined>>({});

  const actorId = user?.id ?? "";
  const canApprove = hasPermission("orders:approve");

  const actorLabIds = useMemo(() => {
    if (!user) return [];

    if (user.permissions.includes("*")) {
      return Array.from(
        new Set(orders.flatMap((order) => (order.items || []).map((item) => item.labId)))
      );
    }

    return user.labId ? [user.labId] : [];
  }, [orders, user]);

  const loadPendingOrders = useCallback(async () => {
    try {
      setLoading(true);

      const response = await requestJson<Order[]>("/api/orders?status=pending_approval");

      setOrders(sortApprovalOrders(response.data));
      setLog(`已載入 ${response.data.length} 筆待簽核委託單`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "載入待簽核委託單失敗";

      setLog(message);
      setModal({ type: "message", title: "載入失敗", message });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMasterData = useCallback(async () => {
    try {
      const response = await requestJson<MasterData>("/api/master-data");

      setMasterData({
        departments: response.data.departments,
        labs: response.data.labs,
        experiments: response.data.experiments,
      });
    } catch (error) {
      setLog(error instanceof Error ? error.message : "載入主資料失敗");
      setMasterData(emptyMasterData);
    }
  }, []);

  const loadUserNames = useCallback(
    async (userIds: string[]) => {
      const missingIds = Array.from(new Set(userIds.filter(Boolean))).filter(
        (id) => id !== actorId && !(id in usersById)
      );

      if (missingIds.length === 0) return;

      const entries = await Promise.all(
        missingIds.map(async (id) => {
          try {
            const user = await userApi.getById(id);
            return [id, user.name] as const;
          } catch {
            return [id, undefined] as const;
          }
        })
      );

      setUsersById((current) => ({
        ...current,
        ...Object.fromEntries(entries),
      }));
    },
    [actorId, usersById]
  );

  const getDetail = useCallback(async (orderId: number) => {
    try {
      const response = await requestJson<Order>(`/api/orders/${orderId}`);

      setModal({
        type: "detail",
        title: `委託單詳細資料｜#${orderId}`,
        order: response.data,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "讀取詳細資料失敗";

      setModal({ type: "message", title: "讀取失敗", message });
    }
  }, []);

  const getHistory = useCallback(async (orderId: number) => {
    try {
      const response = await requestJson<OrderHistory[]>(`/api/orders/${orderId}/history`);

      setModal({
        type: "history",
        title: `委託單流程歷程｜#${orderId}`,
        history: response.data,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "讀取流程歷程失敗";

      setModal({ type: "message", title: "讀取失敗", message });
    }
  }, []);

  const submitAction = useCallback(
    async (
      order: Order,
      action: OrderAction,
      reason?: string,
      orderItemId?: number,
      useQuotaOverride = quotaOverride
    ) => {
      if (order.status !== "pending_approval") {
        setModal({
          type: "message",
          title: "無法執行簽核",
          message: `目前狀態為「${statusLabel[order.status]}」，只有「待簽核」狀態可以核准、退回或拒絕。`,
        });
        return;
      }

      if (!actorId) {
        setModal({
          type: "message",
          title: "尚未登入",
          message: "請先登入後再執行簽核操作。",
        });
        return;
      }

      if (!canApprove) {
        setModal({
          type: "message",
          title: "權限不足",
          message: "目前登入者沒有 orders:approve 權限。",
        });
        return;
      }

      const body: {
        action: OrderAction;
        actorId: string;
        orderItemId?: number;
        reason?: string;
        quotaOverride?: boolean;
      } = { action, actorId };

      if (orderItemId) {
        body.orderItemId = orderItemId;
      }

      if (action === "return" || action === "reject") {
        if (!reason?.trim()) {
          setModal({
            type: "message",
            title: "原因不可為空",
            message: `${actionLabel[action]}必須填寫原因。`,
          });
          return;
        }

        body.reason = reason.trim();
      }

      if (action === "approve" && useQuotaOverride) {
        if (!reason?.trim()) {
          setModal({
            type: "message",
            title: "特批原因不可為空",
            message: "使用 quotaOverride 特批核准時，必須填寫原因。",
          });
          return;
        }

        body.quotaOverride = true;
        body.reason = reason.trim();
      }

      try {
        const response = await requestJson<{ id: number; status: OrderStatus }>(
          `/api/orders/${order.id}/actions`,
          {
            method: "POST",
            body: JSON.stringify(body),
          }
        );

        setLog(JSON.stringify(response, null, 2));
        setModal({
          type: "message",
          title: "簽核操作成功",
          message: `委託單 ${order.orderNo} 已完成「${actionLabel[action]}」。`,
        });
        setReasonModal({ open: false });

        await loadPendingOrders();
      } catch (error) {
        const message = error instanceof Error ? error.message : "簽核操作失敗";

        setLog(message);
        setModal({ type: "message", title: "簽核操作失敗", message });
      }
    },
    [actorId, canApprove, loadPendingOrders, quotaOverride]
  );

  const openReasonModal = useCallback(
    (
      order: Order,
      action: OrderAction,
      orderItem?: OrderItem,
      forceQuotaOverride = false
    ) => {
      const shouldUseQuotaOverride = forceQuotaOverride || quotaOverride;

      if (action === "approve" && !shouldUseQuotaOverride) {
        void submitAction(order, action, undefined, orderItem?.id);
        return;
      }

      const title =
        action === "return"
          ? "填寫退回補件原因"
          : action === "reject"
            ? "填寫拒絕原因"
            : "填寫特批原因";

      const hint =
        action === "return"
          ? `你正在退回委託單 ${order.orderNo}，請填寫需要補件或修改的原因。`
          : action === "reject"
            ? `你正在拒絕委託單 ${order.orderNo}，請填寫拒絕原因。`
            : `你正在以特批方式核准委託單 ${order.orderNo}，請填寫主管特批原因。`;

      setReasonModal({
        open: true,
        title,
        hint,
        action,
        order,
        orderItem,
        quotaOverride: shouldUseQuotaOverride,
        value: "",
      });
    },
    [quotaOverride, submitAction]
  );

  const submitReasonModal = useCallback(() => {
    if (!reasonModal.open) return;

    const reason = reasonModal.value.trim();

    if (!reason) {
      setModal({
        type: "message",
        title: "原因不可為空",
        message: "請填寫原因後再送出。",
      });
      return;
    }

    void submitAction(
      reasonModal.order,
      reasonModal.action,
      reason,
      reasonModal.orderItem?.id,
      reasonModal.quotaOverride || false
    );
  }, [reasonModal, submitAction]);

  useEffect(() => {
    queueMicrotask(() => {
      void loadMasterData();
      void loadPendingOrders();
    });
  }, [loadMasterData, loadPendingOrders]);

  useEffect(() => {
    const userIds = orders.flatMap((order) => [
      order.applicantId,
      ...(order.items || []).flatMap((item) => [item.approvedBy || ""]),
    ]);

    if (modal.type === "detail") {
      userIds.push(
        modal.order.applicantId,
        ...(modal.order.items || []).flatMap((item) => [item.approvedBy || ""])
      );
    }

    if (modal.type === "history") {
      userIds.push(...modal.history.map((item) => item.actorId));
    }

    queueMicrotask(() => {
      void loadUserNames(userIds);
    });
  }, [orders, modal, loadUserNames]);

  return {
    user,
    orders,
    masterData,
    usersById,
    quotaOverride,
    setQuotaOverride,
    loading,
    log,
    modal,
    setModal,
    reasonModal,
    setReasonModal,
    canApprove,
    actorLabIds,
    loadPendingOrders,
    getDetail,
    getHistory,
    openReasonModal,
    submitReasonModal,
  };
}