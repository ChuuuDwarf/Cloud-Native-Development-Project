import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { userApi } from "@/services/user-api";
import { actionLabel, emptyFormItem, emptyMasterData, orderStatusFilters } from "../constants";
import { requestJson } from "../lib/api";
import {
  getEmptyDependencyFlowNames,
  isExperimentItem,
  normalizeDependencyItemsForSubmit,
} from "../lib/dependencyFlows";
import {
  createDefaultItem,
  getNextSampleId,
  getNextSampleIdFromOrders,
  groupItemsBySample,
  toggleExperimentInGroup,
} from "../lib/formItems";
import { readTemplates, writeTemplates } from "../lib/templates";
import type {
  Experiment,
  FormItem,
  MasterData,
  ModalState,
  Order,
  DeliveryDestination,
  OrderAction,
  OrderHistory,
  OrderStatus,
  OrderStatusFilter,
  OrderTemplate,
  PriorityLevel,
  WipDependencyNextData,
  QuotaCheck,
  QuotaSetting,
  SampleFormGroup,
} from "../types";

type OrderItemWithApproval = FormItem & {
  approvedBy?: string | null;
};

type OrderWithEditableFields = Order & {
  priority?: PriorityLevel;
  items?: OrderItemWithApproval[];
};

const deliveryDestinationStoragePrefix = "order-delivery-destination";

function getOrderItems(order: Order): OrderItemWithApproval[] {
  return (order as OrderWithEditableFields).items ?? [];
}

function getOrderPriority(order: Order): PriorityLevel {
  return (order as OrderWithEditableFields).priority ?? "normal";
}

function getUniqueSampleItems(order: Order) {
  const seen = new Set<string>();

  return getOrderItems(order).filter((item) => {
    const sampleId = item.sampleId?.trim();

    if (!sampleId || seen.has(sampleId)) {
      return false;
    }

    seen.add(sampleId);
    return true;
  });
}

function getDeliveryDestinationStorageKey(orderNo: string, sampleId: string) {
  return `${deliveryDestinationStoragePrefix}:${orderNo}:${sampleId}`;
}

function readCachedDeliveryDestination(
  orderNo: string,
  sampleId: string
): DeliveryDestination | null {
  if (typeof window === "undefined") return null;

  try {
    const value = window.localStorage.getItem(getDeliveryDestinationStorageKey(orderNo, sampleId));
    return value ? (JSON.parse(value) as DeliveryDestination) : null;
  } catch {
    return null;
  }
}

function writeCachedDeliveryDestination(orderNo: string, destination: DeliveryDestination) {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(
      getDeliveryDestinationStorageKey(orderNo, destination.sampleId),
      JSON.stringify(destination)
    );
  } catch {
    // Ignore storage failures; the in-memory state still keeps the UI stable.
  }
}

export function useOrdersPage() {
  const { user } = useAuth();

  const currentUserId = user?.id ?? "";
  const currentUserName = user?.name ?? currentUserId;
  const currentDepartmentId = user?.departmentId ?? "";
  const currentUserRole = user?.role ?? "";

  const [orders, setOrders] = useState<Order[]>([]);
  const [masterData, setMasterData] = useState<MasterData>(emptyMasterData);
  const [applicantId, setApplicantId] = useState(currentUserId);
  const [departmentId, setDepartmentId] = useState(currentDepartmentId);
  const [priority, setPriority] = useState<PriorityLevel>("normal");
  const [items, setItems] = useState<FormItem[]>([{ ...emptyFormItem }]);
  const [editingOrderId, setEditingOrderId] = useState<number | null>(null);
  const [editingOrderNo, setEditingOrderNo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [, setLog] = useState("尚未執行操作");
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [quotaCheck, setQuotaCheck] = useState<QuotaCheck | null>(null);
  const [quotaSettings, setQuotaSettings] = useState<QuotaSetting[]>([]);
  const [activeStatusFilter, setActiveStatusFilter] = useState<OrderStatusFilter>("all");
  const [templates, setTemplates] = useState<OrderTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [usersById, setUsersById] = useState<Record<string, string | undefined>>({});
  const [deliveryDestinationsByOrderId, setDeliveryDestinationsByOrderId] = useState<
    Record<number, DeliveryDestination[]>
  >({});
  const [deliveryDestinationLoadingByOrderId, setDeliveryDestinationLoadingByOrderId] = useState<
    Record<number, boolean>
  >({});
  const [deliveryDestinationErrorByOrderId, setDeliveryDestinationErrorByOrderId] = useState<
    Record<number, string | undefined>
  >({});

  const resolveDepartmentId = useCallback(
    (source: MasterData) => {
      const userDepartmentExists = source.departments.some(
        (department) => department.id === currentDepartmentId
      );

      return userDepartmentExists ? currentDepartmentId : source.departments[0]?.id || "";
    },
    [currentDepartmentId]
  );

  const loadMasterData = useCallback(async () => {
    try {
      const response = await requestJson<MasterData>("/api/master-data");
      setMasterData(response.data);

      const firstDepartment = resolveDepartmentId(response.data);
      const firstItem = createDefaultItem(response.data);

      setDepartmentId(firstDepartment);
      setItems([firstItem]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "載入主資料失敗";
      setMasterData(emptyMasterData);
      setLog(message);
    }
  }, [resolveDepartmentId]);

  const loadOrders = useCallback(async () => {
    if (!currentUserId) return;

    try {
      setLoading(true);

      const searchParams = new URLSearchParams();

      if (currentUserRole === "plant_user") {
        searchParams.set("applicantId", currentUserId);
      }

      const queryString = searchParams.toString();
      const path = queryString ? `/api/orders?${queryString}` : "/api/orders";

      const response = await requestJson<Order[]>(path);
      const nextOrders = Array.isArray(response.data) ? response.data : [];

      setOrders(nextOrders);
      setLog(`已載入 ${nextOrders.length} 筆委託單`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "載入委託單失敗";
      setOrders([]);
      setLog(message);
      setModal({ type: "message", title: "載入失敗", message });
    } finally {
      setLoading(false);
    }
  }, [currentUserId, currentUserRole]);

  const loadQuotas = useCallback(async () => {
    try {
      const response = await requestJson<QuotaSetting[]>("/api/quotas");
      setQuotaSettings(response.data);
    } catch (error) {
      setLog(error instanceof Error ? error.message : "載入配額資料失敗");
    }
  }, []);

  const loadUserNames = useCallback(
    async (userIds: string[]) => {
      const missingIds = Array.from(new Set(userIds.filter(Boolean))).filter(
        (id) => id !== currentUserId && !(id in usersById)
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
    [currentUserId, usersById]
  );

  const loadDeliveryDestinations = useCallback(
    async (order: Order) => {
      if (order.status !== "approved") return;
      if (deliveryDestinationLoadingByOrderId[order.id]) return;
      if (order.id in deliveryDestinationsByOrderId) return;

      const sampleItems = getUniqueSampleItems(order);

      if (sampleItems.length === 0) {
        setDeliveryDestinationsByOrderId((current) => ({ ...current, [order.id]: [] }));
        return;
      }

      setDeliveryDestinationLoadingByOrderId((current) => ({ ...current, [order.id]: true }));
      setDeliveryDestinationErrorByOrderId((current) => ({ ...current, [order.id]: undefined }));

      try {
        const destinations = await Promise.all(
          sampleItems.map(async (item) => {
            const cachedDestination = readCachedDeliveryDestination(order.orderNo, item.sampleId);

            if (cachedDestination) {
              return cachedDestination;
            }

            const response = await requestJson<WipDependencyNextData | null>(
              "/api/wips/dependency/next",
              {
                method: "POST",
                body: JSON.stringify({
                  sampleId: item.sampleId,
                  orderNo: order.orderNo,
                }),
              }
            );

            const destination = response.data
              ? ({
                  sampleId: item.sampleId,
                  sampleName: item.sampleName,
                  labName: response.data.labName || "尚未取得送樣地點",
                  experimentName: response.data.experimentName,
                  targetGroup: response.data.targetGroup,
                  target: response.data.target,
                } satisfies DeliveryDestination)
              : ({
                  sampleId: item.sampleId,
                  sampleName: item.sampleName,
                  labName: "尚未取得送樣地點",
                  experimentName: null,
                  targetGroup: item.targetGroup,
                  target: item.target,
                } satisfies DeliveryDestination);

            writeCachedDeliveryDestination(order.orderNo, destination);
            return destination;
          })
        );

        setDeliveryDestinationsByOrderId((current) => ({ ...current, [order.id]: destinations }));
      } catch (error) {
        const message = error instanceof Error ? error.message : "取得送樣地點失敗";

        setDeliveryDestinationErrorByOrderId((current) => ({ ...current, [order.id]: message }));
        setDeliveryDestinationsByOrderId((current) => ({ ...current, [order.id]: [] }));
      } finally {
        setDeliveryDestinationLoadingByOrderId((current) => ({ ...current, [order.id]: false }));
      }
    },
    [deliveryDestinationLoadingByOrderId, deliveryDestinationsByOrderId]
  );

  function loadTemplatesForUser(userId: string) {
    setTemplates(readTemplates(userId));
    setSelectedTemplateId("");
  }

  function saveTemplatesForUser(nextTemplates: OrderTemplate[]) {
    setTemplates(nextTemplates);
    writeTemplates(applicantId, nextTemplates);
  }

  function saveCurrentTemplate() {
    const name = templateName.trim();

    if (!name) {
      setModal({
        type: "message",
        title: "模板名稱不可為空",
        message: "請先輸入模板名稱，再儲存目前的實驗明細。",
      });
      return;
    }

    const nextTemplate: OrderTemplate = {
      id: `${Date.now()}`,
      name,
      items: normalizeDependencyItemsForSubmit(items).map((item) => ({ ...item })),
      createdAt: new Date().toISOString(),
    };

    saveTemplatesForUser([nextTemplate, ...templates]);
    setTemplateName("");
    setSelectedTemplateId(nextTemplate.id);
  }

  function applyTemplate(templateId: string) {
    setSelectedTemplateId(templateId);

    const template = templates.find((item) => item.id === templateId);

    if (!template) return;

    setItems(template.items.map((item) => ({ ...item })));
    setQuotaCheck(null);
  }

  async function checkQuotaForForm() {
    const response = await requestJson<QuotaCheck>(
      `/api/quotas/check?departmentId=${encodeURIComponent(
        departmentId
      )}&itemCount=${normalizeDependencyItemsForSubmit(items).length}&priority=${priority}`
    );

    setQuotaCheck(response.data);
    return response.data;
  }

  function validateForm() {
    if (!currentUserId.trim()) return "請先登入再建立委託單";
    if (!departmentId.trim()) return "部門不可為空";
    if (items.length === 0) return "至少需要一筆實驗明細";

    const emptyFlowNames = getEmptyDependencyFlowNames(items);

    if (emptyFlowNames.length > 0) {
      return `${emptyFlowNames[0]} 尚未加入任何實驗，請先加入實驗或移除此流程`;
    }

    const invalidIndex = items.findIndex(
      (item) =>
        isExperimentItem(item) &&
        (!item.sampleId.trim() || !item.labId.trim() || !item.experimentId.trim())
    );

    if (invalidIndex >= 0) {
      return `明細 ${invalidIndex + 1} 的樣品、實驗室、實驗項目都需要填寫`;
    }

    const invalidDependencyIndex = items.findIndex(
      (item) => isExperimentItem(item) && (!item.targetGroup.trim() || item.target < 1)
    );

    if (invalidDependencyIndex >= 0) {
      return `第 ${invalidDependencyIndex + 1} 筆相依流程設定不完整`;
    }

    return null;
  }

  const safeOrders = Array.isArray(orders) ? orders : [];

  const visibleOrders =
    currentUserRole === "plant_user"
      ? safeOrders.filter((order) => order.applicantId === currentUserId)
      : safeOrders;

  function resetForm() {
    setEditingOrderId(null);
    setEditingOrderNo(null);
    setApplicantId(currentUserId);
    setDepartmentId(resolveDepartmentId(masterData));
    setPriority("normal");

    const nextSampleId = getNextSampleIdFromOrders(visibleOrders);
    setItems([createDefaultItem(masterData, nextSampleId)]);

    setQuotaCheck(null);
  }

  function openCreateOrder() {
    resetForm();
    setFormModalOpen(true);
  }

  function closeFormModal() {
    resetForm();
    setFormModalOpen(false);
  }

  function startEditOrder(order: Order) {
    if (order.status !== "draft" && order.status !== "returned") {
      setModal({
        type: "message",
        title: "不可編輯",
        message: "只有草稿或退回補件的委託單可以修改。",
      });
      return;
    }

    const orderItems = getOrderItems(order);

    setEditingOrderId(order.id);
    setEditingOrderNo(order.orderNo);
    setApplicantId(order.applicantId);
    setDepartmentId(order.departmentId);
    setPriority(getOrderPriority(order));
    setItems(
      orderItems.length
        ? orderItems.map(
            ({ sampleId, sampleName, labId, experimentId, targetGroup, target, check }) => ({
              sampleId,
              sampleName: sampleName ?? "",
              labId,
              experimentId,
              targetGroup: targetGroup || "G1",
              target: target || 1,
              check: check ?? false,
            })
          )
        : [createDefaultItem(masterData)]
    );
    setFormModalOpen(true);
  }

  async function createOrder(submitAfterCreate = false) {
    if (submitting) return;

    const error = validateForm();

    if (error) {
      setModal({
        type: "message",
        title: "表單資料不完整",
        message: error,
      });
      return;
    }

    try {
      setSubmitting(true);
      const submitItems = normalizeDependencyItemsForSubmit(items);

      const response = await requestJson<Order>("/api/orders", {
        method: "POST",
        body: JSON.stringify({ departmentId, priority, items: submitItems }),
      });

      let check: QuotaCheck | null = null;

      try {
        check = await checkQuotaForForm();
      } catch (quotaError) {
        setLog(quotaError instanceof Error ? quotaError.message : "配額檢查失敗");
      }

      if (submitAfterCreate) {
        await requestJson<{ id: number; status: OrderStatus }>(
          `/api/orders/${response.data.id}/actions`,
          {
            method: "POST",
            body: JSON.stringify({ action: "submit" }),
          }
        );
      }

      setLog(JSON.stringify(response, null, 2));
      setModal({
        type: "message",
        title: submitAfterCreate ? "已建立並送出" : "已建立草稿",
        message: submitAfterCreate
          ? `委託單 ${response.data.orderNo} 已建立並送出簽核。${
              check?.needOverride ? " 部分子單需主管特批。" : ""
            }`
          : `委託單 ${response.data.orderNo} 已儲存為草稿。`,
      });

      resetForm();
      setFormModalOpen(false);
      await loadOrders();
      await loadQuotas();
    } catch (error) {
      const message = error instanceof Error ? error.message : "建立委託單失敗";
      setLog(message);
      setModal({ type: "message", title: "建立失敗", message });
    } finally {
      setSubmitting(false);
    }
  }

  async function updateOrder() {
    if (editingOrderId === null) {
      setModal({
        type: "message",
        title: "尚未選擇委託單",
        message: "請先從列表選擇要修改的草稿或退回補件委託單。",
      });
      return;
    }

    const error = validateForm();

    if (error) {
      setModal({
        type: "message",
        title: "表單資料不完整",
        message: error,
      });
      return;
    }

    try {
      const submitItems = normalizeDependencyItemsForSubmit(items);
      const response = await requestJson<Order>(`/api/orders/${editingOrderId}`, {
        method: "PATCH",
        body: JSON.stringify({ departmentId, priority, items: submitItems }),
      });

      setLog(JSON.stringify(response, null, 2));
      setModal({
        type: "message",
        title: "更新成功",
        message: `委託單 ${editingOrderNo} 已更新，可以重新送出簽核。`,
      });

      resetForm();
      setFormModalOpen(false);
      await loadOrders();
    } catch (error) {
      const message = error instanceof Error ? error.message : "更新委託單失敗";
      setLog(message);
      setModal({ type: "message", title: "更新失敗", message });
    }
  }

  async function getDetail(orderId: number) {
    try {
      const response = await requestJson<Order>(`/api/orders/${orderId}`);
      setModal({
        type: "detail",
        title: `委託單詳細 #${orderId}`,
        order: response.data,
      });
    } catch (error) {
      setModal({
        type: "message",
        title: "讀取失敗",
        message: error instanceof Error ? error.message : "載入委託單失敗",
      });
    }
  }

  async function getHistory(orderId: number) {
    try {
      const response = await requestJson<OrderHistory[]>(`/api/orders/${orderId}/history`);

      setModal({
        type: "history",
        title: `委託單流程歷程 #${orderId}`,
        history: response.data,
      });
    } catch (error) {
      setModal({
        type: "message",
        title: "讀取失敗",
        message: error instanceof Error ? error.message : "載入委託單失敗",
      });
    }
  }

  async function doAction(order: Order, action: OrderAction) {
    try {
      const response = await requestJson<{ id: number; status: OrderStatus }>(
        `/api/orders/${order.id}/actions`,
        {
          method: "POST",
          body: JSON.stringify({ action }),
        }
      );

      setLog(JSON.stringify(response, null, 2));
      setModal({
        type: "message",
        title: "操作成功",
        message: `委託單 ${order.orderNo} 已執行：${actionLabel[action]}。`,
      });

      await loadOrders();
      await loadQuotas();
    } catch (error) {
      const message = error instanceof Error ? error.message : "操作失敗";
      setLog(message);
      setModal({ type: "message", title: "操作失敗", message });
    }
  }

  async function deleteOrder(order: Order) {
    if (order.status !== "draft") {
      setModal({
        type: "message",
        title: "不可刪除",
        message: "只有草稿委託單可以刪除。",
      });
      return;
    }

    if (!window.confirm(`確認刪除草稿委託單 ${order.orderNo}？`)) return;

    try {
      const response = await requestJson<{ id: number }>(`/api/orders/${order.id}`, {
        method: "DELETE",
      });

      setLog(JSON.stringify(response, null, 2));
      setModal({
        type: "message",
        title: "刪除成功",
        message: `委託單 ${order.orderNo} 已刪除。`,
      });

      await loadOrders();
      await loadQuotas();
    } catch (error) {
      const message = error instanceof Error ? error.message : "操作失敗";
      setLog(message);
      setModal({ type: "message", title: "刪除失敗", message });
    }
  }

  function addSample() {
    setItems((current) => [...current, createDefaultItem(masterData, getNextSampleId(current))]);
  }

  function removeItem(index: number) {
    setItems((current) =>
      current.length <= 1 ? current : current.filter((_, itemIndex) => itemIndex !== index)
    );
  }

  function updateSampleGroup(group: SampleFormGroup, sampleId: string) {
    setItems((current) =>
      current.map((item, index) =>
        index >= group.startIndex && index <= group.endIndex ? { ...item, sampleId } : item
      )
    );
  }

  function updateSampleNameGroup(group: SampleFormGroup, sampleName: string) {
    setItems((current) =>
      current.map((item, index) =>
        index >= group.startIndex && index <= group.endIndex ? { ...item, sampleName } : item
      )
    );
  }

  function updateDependencyItems(group: SampleFormGroup, nextItems: FormItem[]) {
    const replacementItems =
      nextItems.length > 0
        ? nextItems
        : [
            {
              sampleId: group.sampleId,
              sampleName: group.sampleName,
              labId: "",
              experimentId: "",
              targetGroup: "G1",
              target: 1,
              check: false,
            },
          ];

    setItems((current) =>
      current.flatMap((item, index) => {
        if (index === group.startIndex) return replacementItems;
        if (index > group.startIndex && index <= group.endIndex) return [];
        return [item];
      })
    );
  }

  function moveExperiment(index: number, direction: -1 | 1) {
    setItems((current) => {
      const targetIndex = index + direction;
      const item = current[index];
      const target = current[targetIndex];

      if (!item || !target || item.sampleId !== target.sampleId) {
        return current;
      }

      const next = [...current];
      [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
      return next;
    });
  }

  function toggleExperimentForSample(
    group: SampleFormGroup,
    experiment: Experiment,
    checked: boolean
  ) {
    setItems((current) => toggleExperimentInGroup(current, group, experiment, checked));
  }

  useEffect(() => {
    if (!currentUserId) return;

    queueMicrotask(() => {
      setApplicantId(currentUserId);

      if (
        currentDepartmentId &&
        masterData.departments.some((department) => department.id === currentDepartmentId)
      ) {
        setDepartmentId(currentDepartmentId);
      }
    });
  }, [currentUserId, currentDepartmentId, masterData.departments]);

  useEffect(() => {
    if (!currentUserId) return;

    queueMicrotask(() => {
      void loadMasterData();
      void loadOrders();
      void loadQuotas();
    });
  }, [currentUserId, loadMasterData, loadOrders, loadQuotas]);

  useEffect(() => {
    if (!applicantId) return;

    queueMicrotask(() => loadTemplatesForUser(applicantId));
  }, [applicantId]);

  useEffect(() => {
    const userIds = visibleOrders.flatMap((order) => [
      order.applicantId,
      ...getOrderItems(order).flatMap((item) => [item.approvedBy || ""]),
    ]);

    userIds.push(
      ...quotaSettings.filter((quota) => quota.scopeType === "user").map((quota) => quota.scopeId)
    );

    if (modal.type === "detail") {
      userIds.push(
        modal.order.applicantId,
        ...getOrderItems(modal.order).flatMap((item) => [item.approvedBy || ""])
      );
    }

    if (modal.type === "history") {
      userIds.push(...modal.history.map((item) => item.actorId));
    }

    queueMicrotask(() => void loadUserNames(userIds));
  }, [visibleOrders, quotaSettings, modal, loadUserNames]);

  useEffect(() => {
    const approvedOrders = visibleOrders.filter((order) => order.status === "approved");

    approvedOrders.forEach((order) => {
      void loadDeliveryDestinations(order);
    });
  }, [visibleOrders, loadDeliveryDestinations]);

  const statusCounts = useMemo(
    () =>
      orderStatusFilters.reduce<Record<OrderStatusFilter, number>>(
        (counts, filter) => {
          counts[filter.value] =
            filter.value === "all"
              ? visibleOrders.length
              : visibleOrders.filter((order) => order.status === filter.value).length;

          return counts;
        },
        {} as Record<OrderStatusFilter, number>
      ),
    [visibleOrders]
  );

  const filteredOrders =
    activeStatusFilter === "all"
      ? visibleOrders
      : visibleOrders.filter((order) => order.status === activeStatusFilter);

  const sampleGroups = groupItemsBySample(items);

  return {
    currentUserId,
    currentUserName,
    currentUserRole,
    currentDepartmentId,
    applicantId,
    departmentId,
    setDepartmentId,
    priority,
    setPriority,
    items,
    masterData,
    usersById,
    deliveryDestinationsByOrderId,
    deliveryDestinationLoadingByOrderId,
    deliveryDestinationErrorByOrderId,
    editingOrderId,
    editingOrderNo,
    loading,
    modal,
    setModal,
    formModalOpen,
    submitting,
    quotaCheck,
    quotaSettings,
    templates,
    selectedTemplateId,
    templateName,
    setTemplateName,
    activeStatusFilter,
    setActiveStatusFilter,
    filteredOrders,
    orders: visibleOrders,
    statusCounts,
    sampleGroups,
    loadOrders,
    loadQuotas,
    openCreateOrder,
    closeFormModal,
    startEditOrder,
    createOrder,
    updateOrder,
    getDetail,
    getHistory,
    doAction,
    deleteOrder,
    checkQuotaForForm,
    saveCurrentTemplate,
    applyTemplate,
    setSelectedTemplateId,
    addSample,
    removeItem,
    updateSampleGroup,
    updateSampleNameGroup,
    updateDependencyItems,
    moveExperiment,
    toggleExperimentForSample,
  };
}
