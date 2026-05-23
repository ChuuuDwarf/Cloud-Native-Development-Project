"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { CSSProperties } from "react";

type OrderStatus =
  | "draft"
  | "pending_approval"
  | "cancelled"
  | "approved"
  | "returned"
  | "rejected"
  | "sample_delivered"
  | "sample_received"
  | "ready_for_pickup"
  | "closed";

type OrderAction =
  | "submit"
  | "cancel"
  | "confirm_delivery"
  | "confirm_received"
  | "ready_for_pickup"
  | "close";

type PriorityLevel = "normal" | "urgent" | "critical";

type OrderStatusFilter = "all" | OrderStatus;

type Department = {
  id: string;
  name: string;
};

type Lab = {
  id: string;
  name: string;
};

type Experiment = {
  id: string;
  name: string;
  labId: string;
};

type MasterData = {
  departments: Department[];
  labs: Lab[];
  experiments: Experiment[];
  statuses?: { value: string; label: string }[];
};

type FormItem = {
  sampleId: string;
  labId: string;
  experimentId: string;
};

type OrderTemplate = {
  id: string;
  name: string;
  items: FormItem[];
  createdAt: string;
};

type OrderItem = {
  id: number;
  sampleId: string;
  labId: string;
  experimentId: string;
  status?: OrderStatus;
  approvedBy?: string | null;
  approvedAt?: string | null;
  returnReason?: string | null;
  rejectReason?: string | null;
  quotaExceeded?: boolean;
  quotaOverride?: boolean;
};

type Order = {
  id: number;
  orderNo: string;
  applicantId: string;
  departmentId: string;
  applyDate: string;
  status: OrderStatus;
  priority?: PriorityLevel;
  totalItems: number;
  lastReason?: string | null;
  createdAt: string;
  updatedAt: string;
  items?: OrderItem[];
};

type OrderHistory = {
  id: number;
  orderId: number;
  actorId: string;
  action: string;
  fromStatus?: string | null;
  toStatus: string;
  reason?: string | null;
  quotaOverride: boolean;
  actionTime: string;
};

type ApiResponse<T> = {
  success: boolean;
  data: T;
  message?: string;
};

type QuotaCheckItem = {
  scopeType: string;
  scopeId: string;
  used: number;
  limit: number;
  requested: number;
  allowed: boolean;
  needOverride: boolean;
};

type QuotaCheck = {
  allowed: boolean;
  needOverride: boolean;
  checks: QuotaCheckItem[];
};

type QuotaSetting = {
  id: number;
  scopeType: string;
  scopeId: string;
  monthlyLimit: number;
  isActive: boolean;
  usedCount?: number;
  remaining?: number;
};

type ModalState =
  | { type: "none" }
  | { type: "message"; title: string; message: string }
  | { type: "detail"; title: string; order: Order }
  | { type: "history"; title: string; history: OrderHistory[] };

const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const templateStoragePrefix = "order-management-templates";

const emptyFormItem: FormItem = {
  sampleId: "S001",
  labId: "LAB001",
  experimentId: "EXP001",
};

const defaultMasterData: MasterData = {
  departments: [
    { id: "D001", name: "製造一部" },
    { id: "D002", name: "品保部" },
  ],
  labs: [
    { id: "LAB001", name: "可靠度實驗室" },
    { id: "LAB002", name: "材料分析實驗室" },
  ],
  experiments: [
    { id: "EXP001", name: "溫濕度測試", labId: "LAB001" },
    { id: "EXP002", name: "壽命測試", labId: "LAB001" },
    { id: "EXP003", name: "成分分析", labId: "LAB002" },
  ],
};

const statusLabel: Record<OrderStatus, string> = {
  draft: "草稿",
  pending_approval: "待簽核",
  cancelled: "已取消",
  approved: "已核准",
  returned: "退回補件",
  rejected: "已拒絕",
  sample_delivered: "已送樣",
  sample_received: "已收樣",
  ready_for_pickup: "待取件",
  closed: "已結案",
};

const priorityLabel: Record<PriorityLevel, string> = {
  normal: "一般",
  urgent: "急件",
  critical: "特急件",
};

const actionLabel: Record<OrderAction, string> = {
  submit: "送出簽核",
  cancel: "取消委託單",
  confirm_delivery: "確認送樣",
  confirm_received: "確認收樣",
  ready_for_pickup: "待取件",
  close: "結案",
};

const allowedActions: Record<OrderStatus, OrderAction[]> = {
  draft: ["submit", "cancel"],
  returned: ["submit", "cancel"],
  pending_approval: ["cancel"],
  approved: ["confirm_delivery"],
  sample_delivered: ["confirm_received"],
  sample_received: ["ready_for_pickup"],
  ready_for_pickup: ["close"],
  closed: [],
  rejected: [],
  cancelled: [],
};

const orderStatusFilters: { value: OrderStatusFilter; label: string }[] = [
  { value: "all", label: "所有委託單" },
  { value: "draft", label: "草稿" },
  { value: "pending_approval", label: "待簽核" },
  { value: "returned", label: "退回補件" },
  { value: "rejected", label: "已拒絕" },
  { value: "approved", label: "已核准" },
  { value: "sample_delivered", label: "已送樣" },
  { value: "sample_received", label: "已收樣" },
  { value: "ready_for_pickup", label: "待取件" },
  { value: "closed", label: "已結案" },
  { value: "cancelled", label: "已取消" },
];

async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : typeof payload === "object" && payload && "message" in payload
          ? String((payload as { message: unknown }).message)
          : "API request failed";

    throw new Error(message);
  }

  return payload as ApiResponse<T>;
}

function formatDate(value?: string | null) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getEffectiveItemStatus(order: Order, item: OrderItem) {
  if (order.status === "pending_approval" && (!item.status || item.status === "draft")) {
    return "pending_approval";
  }

  return item.status || "-";
}

function quotaStatusText(item: OrderItem) {
  if (item.quotaOverride) return "配額：已特批";
  if (item.quotaExceeded) return "配額：需特批";
  return "配額：正常";
}

function templateStorageKey(applicantId: string) {
  return `${templateStoragePrefix}:${applicantId || "anonymous"}`;
}

type SampleFormGroup = {
  sampleId: string;
  startIndex: number;
  endIndex: number;
  items: { item: FormItem; index: number }[];
};

function groupItemsBySample(formItems: FormItem[]): SampleFormGroup[] {
  return formItems.reduce<SampleFormGroup[]>((groups, item, index) => {
    const lastGroup = groups.at(-1);

    if (lastGroup && lastGroup.sampleId === item.sampleId) {
      lastGroup.endIndex = index;
      lastGroup.items.push({ item, index });
      return groups;
    }

    groups.push({
      sampleId: item.sampleId,
      startIndex: index,
      endIndex: index,
      items: [{ item, index }],
    });
    return groups;
  }, []);
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [masterData, setMasterData] = useState<MasterData>(defaultMasterData);

  const [applicantId, setApplicantId] = useState("user001");
  const [departmentId, setDepartmentId] = useState("D001");
  const [priority, setPriority] = useState<PriorityLevel>("normal");
  const [items, setItems] = useState<FormItem[]>([emptyFormItem]);

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

  async function loadMasterData() {
    try {
      const response = await requestJson<MasterData>("/api/master-data");
      setMasterData(response.data);

      const firstDepartment = response.data.departments[0]?.id || "D001";
      const firstLab = response.data.labs[0]?.id || "LAB001";
      const firstExperiment =
        response.data.experiments.find((experiment) => experiment.labId === firstLab)?.id ||
        "EXP001";

      setDepartmentId(firstDepartment);
      setItems([
        {
          sampleId: "S001",
          labId: firstLab,
          experimentId: firstExperiment,
        },
      ]);
    } catch {
      setMasterData(defaultMasterData);
    }
  }

  async function loadOrders() {
    try {
      setLoading(true);
      const response = await requestJson<Order[]>("/api/orders");
      setOrders(response.data);
      setLog(`已載入 ${response.data.length} 筆委託單`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "載入委託單失敗";
      setLog(message);
      setModal({
        type: "message",
        title: "載入失敗",
        message,
      });
    } finally {
      setLoading(false);
    }
  }

  async function loadQuotas() {
    try {
      const response = await requestJson<QuotaSetting[]>("/api/quotas");
      setQuotaSettings(response.data);
    } catch (error) {
      setLog(error instanceof Error ? error.message : "載入配額資料失敗");
    }
  }

  function loadTemplatesForUser(userId: string) {
    if (typeof window === "undefined") return;

    try {
      const raw = window.localStorage.getItem(templateStorageKey(userId));
      const parsed = raw ? (JSON.parse(raw) as OrderTemplate[]) : [];
      setTemplates(Array.isArray(parsed) ? parsed : []);
      setSelectedTemplateId("");
    } catch {
      setTemplates([]);
      setSelectedTemplateId("");
    }
  }

  function saveTemplatesForUser(nextTemplates: OrderTemplate[]) {
    setTemplates(nextTemplates);
    window.localStorage.setItem(templateStorageKey(applicantId), JSON.stringify(nextTemplates));
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
      items: items.map((item) => ({ ...item })),
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
      `/api/quotas/check?applicantId=${encodeURIComponent(applicantId)}&departmentId=${encodeURIComponent(departmentId)}&itemCount=${items.length}&priority=${priority}`
    );
    setQuotaCheck(response.data);
    return response.data;
  }

  function validateForm() {
    if (!applicantId.trim()) return "申請人不可為空";
    if (!departmentId.trim()) return "部門不可為空";
    if (items.length === 0) return "至少需要一筆實驗明細";

    const invalidIndex = items.findIndex(
      (item) => !item.sampleId.trim() || !item.labId.trim() || !item.experimentId.trim()
    );

    if (invalidIndex >= 0) {
      return `明細 ${invalidIndex + 1} 的樣品、實驗室、實驗項目都需要填寫`;
    }

    return null;
  }

  function resetForm() {
    setEditingOrderId(null);
    setEditingOrderNo(null);
    setApplicantId("user001");
    setDepartmentId(masterData.departments[0]?.id || "D001");
    setPriority("normal");

    const firstLab = masterData.labs[0]?.id || "LAB001";
    const firstExperiment =
      masterData.experiments.find((experiment) => experiment.labId === firstLab)?.id || "EXP001";

    setItems([
      {
        sampleId: "S001",
        labId: firstLab,
        experimentId: firstExperiment,
      },
    ]);
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

    setEditingOrderId(order.id);
    setEditingOrderNo(order.orderNo);
    setApplicantId(order.applicantId);
    setDepartmentId(order.departmentId);
    setPriority(order.priority || "normal");

    if (order.items && order.items.length > 0) {
      setItems(
        order.items.map((item) => ({
          sampleId: item.sampleId,
          labId: item.labId,
          experimentId: item.experimentId,
        }))
      );
    } else {
      setItems([emptyFormItem]);
    }
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
      const response = await requestJson<Order>("/api/orders", {
        method: "POST",
        body: JSON.stringify({
          applicantId,
          departmentId,
          priority,
          items,
        }),
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
            body: JSON.stringify({
              action: "submit",
              actorId: applicantId,
            }),
          }
        );
      }

      setLog(JSON.stringify(response, null, 2));
      setModal({
        type: "message",
        title: submitAfterCreate ? "已建立並送出" : "已建立草稿",
        message: submitAfterCreate
          ? `委託單 ${response.data.orderNo} 已建立並送出簽核。${check?.needOverride ? " 部分子單需主管特批。" : ""}`
          : `委託單 ${response.data.orderNo} 已儲存為草稿。`,
      });

      resetForm();
      setFormModalOpen(false);
      await loadOrders();
      await loadQuotas();
    } catch (error) {
      const message = error instanceof Error ? error.message : "建立委託單失敗";
      setLog(message);
      setModal({
        type: "message",
        title: "建立失敗",
        message,
      });
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
      const response = await requestJson<Order>(`/api/orders/${editingOrderId}`, {
        method: "PATCH",
        body: JSON.stringify({
          departmentId,
          priority,
          items,
        }),
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
      setModal({
        type: "message",
        title: "更新成功",
        message,
      });
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
      const message = error instanceof Error ? error.message : "載入委託單失敗";
      setModal({
        type: "message",
        title: "讀取失敗",
        message,
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
      const message = error instanceof Error ? error.message : "載入委託單失敗";
      setModal({
        type: "message",
        title: "讀取失敗",
        message,
      });
    }
  }

  async function doAction(order: Order, action: OrderAction) {
    try {
      const response = await requestJson<{ id: number; status: OrderStatus }>(
        `/api/orders/${order.id}/actions`,
        {
          method: "POST",
          body: JSON.stringify({
            action,
            actorId:
              action === "confirm_received" || action === "ready_for_pickup" || action === "close"
                ? "labstaff001"
                : "user001",
          }),
        }
      );

      setLog(JSON.stringify(response, null, 2));

      setModal({
        type: "message",
        title: "操作成功",
        message: `委託單 ${order.orderNo} 已執行：${actionLabel[action]}。`,
      });

      await loadOrders();
    } catch (error) {
      const message = error instanceof Error ? error.message : "操作失敗";
      setLog(message);
      setModal({
        type: "message",
        title: "操作失敗",
        message,
      });
    }
  }

  async function deleteOrder(order: Order) {
    if (order.status !== "draft") {
      setModal({
        type: "message",
        title: "不可刪除",
        message: "只有草稿或退回補件的委託單可以修改。",
      });
      return;
    }

    const confirmed = window.confirm(`確認刪除草稿委託單 ${order.orderNo}？`);

    if (!confirmed) return;

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
    } catch (error) {
      const message = error instanceof Error ? error.message : "操作失敗";
      setLog(message);
      setModal({
        type: "message",
        title: "刪除失敗",
        message,
      });
    }
  }

  function defaultExperimentForLab(labId: string) {
    return masterData.experiments.find((experiment) => experiment.labId === labId)?.id || "";
  }

  function defaultItem(sampleId: string): FormItem {
    const firstLab = masterData.labs[0]?.id || "LAB001";
    return {
      sampleId,
      labId: firstLab,
      experimentId: defaultExperimentForLab(firstLab) || "EXP001",
    };
  }

  function addSample() {
    setItems((current) => [...current, defaultItem(`S${String(Date.now()).slice(-5)}`)]);
  }

  function removeItem(index: number) {
    setItems((current) => {
      if (current.length <= 1) return current;
      return current.filter((_, itemIndex) => itemIndex !== index);
    });
  }

  function updateSampleGroup(group: SampleFormGroup, sampleId: string) {
    setItems((current) =>
      current.map((item, index) =>
        index >= group.startIndex && index <= group.endIndex ? { ...item, sampleId } : item
      )
    );
  }

  function moveExperiment(index: number, direction: -1 | 1) {
    setItems((current) => {
      const targetIndex = index + direction;
      const item = current[index];
      const target = current[targetIndex];

      if (!item || !target || item.sampleId !== target.sampleId) return current;

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
    setItems((current) => {
      const existingIndex = current.findIndex(
        (item, index) =>
          index >= group.startIndex &&
          index <= group.endIndex &&
          item.experimentId === experiment.id
      );

      if (checked) {
        if (existingIndex >= 0) return current;

        const next = [...current];
        next.splice(group.endIndex + 1, 0, {
          sampleId: group.sampleId || "S001",
          labId: experiment.labId,
          experimentId: experiment.id,
        });
        return next;
      }

      if (existingIndex < 0 || current.length <= 1) return current;
      return current.filter((_, index) => index !== existingIndex);
    });
  }

  useEffect(() => {
    queueMicrotask(() => {
      void loadMasterData();
      void loadOrders();
      void loadQuotas();
    });
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      loadTemplatesForUser(applicantId);
    });
  }, [applicantId]);

  const statusCounts = orderStatusFilters.reduce<Record<OrderStatusFilter, number>>(
    (counts, filter) => {
      counts[filter.value] =
        filter.value === "all"
          ? orders.length
          : orders.filter((order) => order.status === filter.value).length;
      return counts;
    },
    {} as Record<OrderStatusFilter, number>
  );

  const filteredOrders =
    activeStatusFilter === "all"
      ? orders
      : orders.filter((order) => order.status === activeStatusFilter);

  const sampleGroups = groupItemsBySample(items);

  const orderForm = (
    <>
      {editingOrderId && (
        <div style={editNoticeStyle}>正在修改委託單 {editingOrderNo}，修改後可以重新送出簽核。</div>
      )}

      <Field label="申請人">
        <Input value={applicantId} onChange={setApplicantId} disabled={editingOrderId !== null} />
      </Field>

      <Field label="部門 / 廠區">
        <select
          value={departmentId}
          onChange={(event) => setDepartmentId(event.target.value)}
          style={inputStyle}
        >
          {masterData.departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name} ({department.id})
            </option>
          ))}
        </select>
      </Field>

      <Field label="優先程度">
        <select
          value={priority}
          onChange={(event) => setPriority(event.target.value as PriorityLevel)}
          style={inputStyle}
        >
          <option value="normal">一般</option>
          <option value="urgent">急件</option>
          <option value="critical">特急件</option>
        </select>
      </Field>

      <div style={{ marginTop: 12 }}>
        <button type="button" onClick={() => void checkQuotaForForm()} style={buttonStyle("blue")}>
          檢查配額
        </button>
      </div>

      {quotaCheck && (
        <div style={quotaBoxStyle}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>
            {quotaCheck.needOverride ? "配額檢查：超額，需主管特批" : "配額檢查：可送出"}
          </div>
          {quotaCheck.checks.map((check) => (
            <div
              key={`${check.scopeType}-${check.scopeId}`}
              style={{ fontSize: 12, color: "var(--text2)", marginTop: 4 }}
            >
              {check.scopeType}/{check.scopeId}：已用 {check.used} / 上限 {check.limit}，本次{" "}
              {check.requested}
            </div>
          ))}
        </div>
      )}

      <div style={templateBoxStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontWeight: 800 }}>常用實驗模板</div>
            <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 4 }}>
              可將目前明細儲存為模板，之後快速套用。
            </div>
          </div>
          <span style={{ color: "var(--text3)", fontSize: 12 }}>{templates.length} 個模板</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, marginTop: 12 }}>
          <input
            value={templateName}
            onChange={(event) => setTemplateName(event.target.value)}
            placeholder="輸入模板名稱，例如：可靠度常測 3 項"
            style={inputStyle}
          />
          <button type="button" onClick={saveCurrentTemplate} style={buttonStyle("green")}>
            儲存模板
          </button>
        </div>

        {templates.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, marginTop: 10 }}>
            <select
              value={selectedTemplateId}
              onChange={(event) => applyTemplate(event.target.value)}
              style={inputStyle}
            >
              <option value="">選擇模板套用</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}（{template.items.length} 筆）
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => selectedTemplateId && applyTemplate(selectedTemplateId)}
              style={buttonStyle("blue")}
              disabled={!selectedTemplateId}
            >
              套用
            </button>
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: 16,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14 }}>樣品與實驗順序</h3>
        <button type="button" onClick={addSample} style={buttonStyle("blue")}>
          新增樣品
        </button>
      </div>

      <div style={{ display: "grid", gap: 12, marginTop: 10 }}>
        {sampleGroups.map((group, groupIndex) => (
          <div key={`${group.startIndex}-${group.sampleId}`} style={itemCardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <strong style={{ fontSize: 13 }}>樣品 {groupIndex + 1}</strong>
              <span style={{ color: "var(--text3)", fontSize: 12 }}>
                已選 {group.items.length} 項實驗
              </span>
            </div>

            <Field label="樣品編號">
              <Input value={group.sampleId} onChange={(value) => updateSampleGroup(group, value)} />
            </Field>

            <div style={experimentChecklistStyle}>
              {masterData.labs.map((lab) => {
                const labExperiments = masterData.experiments.filter(
                  (experiment) => experiment.labId === lab.id
                );

                if (labExperiments.length === 0) return null;

                return (
                  <div key={lab.id} style={experimentLabGroupStyle}>
                    <div style={{ fontWeight: 800, fontSize: 12, color: "var(--text2)" }}>
                      {lab.name} ({lab.id})
                    </div>
                    <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
                      {labExperiments.map((experiment) => {
                        const checked = group.items.some(
                          ({ item }) => item.experimentId === experiment.id
                        );

                        return (
                          <label key={experiment.id} style={checkboxRowStyle}>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(event) =>
                                toggleExperimentForSample(group, experiment, event.target.checked)
                              }
                            />
                            <span>
                              {experiment.name} ({experiment.id})
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
              {group.items.map(({ item, index }, experimentIndex) => {
                const lab = masterData.labs.find((candidate) => candidate.id === item.labId);
                const experiment = masterData.experiments.find(
                  (candidate) => candidate.id === item.experimentId
                );
                const canMoveUp = experimentIndex > 0;
                const canMoveDown = experimentIndex < group.items.length - 1;

                return (
                  <div
                    key={`${index}-${item.labId}-${item.experimentId}`}
                    style={{
                      borderTop: "1px solid var(--border)",
                      paddingTop: 10,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 8,
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <strong style={{ fontSize: 13 }}>實驗 {experimentIndex + 1}</strong>
                      <span style={{ color: "var(--text2)", fontSize: 12 }}>
                        {lab?.name || item.labId} / {experiment?.name || item.experimentId}
                      </span>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button
                          type="button"
                          onClick={() => moveExperiment(index, -1)}
                          style={buttonStyle("gray")}
                          disabled={!canMoveUp}
                        >
                          上移
                        </button>
                        <button
                          type="button"
                          onClick={() => moveExperiment(index, 1)}
                          style={buttonStyle("gray")}
                          disabled={!canMoveDown}
                        >
                          下移
                        </button>
                        {items.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeItem(index)}
                            style={buttonStyle("red")}
                          >
                            移除
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {editingOrderId ? (
        <button
          type="button"
          onClick={() => void updateOrder()}
          style={{ ...buttonStyle("green"), width: "100%", marginTop: 14 }}
        >
          儲存修改
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={closeFormModal}
            style={{ ...buttonStyle("gray"), width: "100%", marginTop: 14 }}
          >
            取消離開
          </button>
          <button
            type="button"
            onClick={() => void createOrder(false)}
            disabled={submitting}
            style={{ ...buttonStyle("green"), width: "100%", marginTop: 8 }}
          >
            {submitting ? "處理中..." : "建立草稿"}
          </button>
          <button
            type="button"
            onClick={() => void createOrder(true)}
            disabled={submitting}
            style={{ ...buttonStyle("blue"), width: "100%", marginTop: 8 }}
          >
            {submitting ? "處理中..." : "直接送出"}
          </button>
        </>
      )}
    </>
  );

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>委託單管理</h1>
        <p style={{ color: "var(--text3)", fontSize: 12, marginTop: 4, fontFamily: "monospace" }}>
          ORDER MANAGEMENT · 建立、送出、修改補件與追蹤送測申請
        </p>
      </div>

      <div style={{ display: "grid", gap: 16 }}>
        <div style={orderWorkspaceGridStyle}>
          <section style={quotaSummaryStyle}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                alignItems: "flex-start",
              }}
            >
              <div>
                <h2 style={summaryTitleStyle}>配額用量</h2>
                <p style={summaryTextStyle}>顯示個人與部門配額明細</p>
              </div>
              <button type="button" onClick={() => void loadQuotas()} style={buttonStyle("blue")}>
                更新
              </button>
            </div>

            {quotaSettings.length === 0 ? (
              <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 12 }}>
                目前沒有配額資料
              </div>
            ) : (
              <div style={quotaDetailListStyle}>
                {quotaSettings.map((quota) => (
                  <div key={quota.id} style={quotaSummaryItemStyle}>
                    <div style={{ fontWeight: 800 }}>
                      {quota.scopeType === "user"
                        ? "個人"
                        : quota.scopeType === "department"
                          ? "部門"
                          : quota.scopeType}
                      ：{quota.scopeId}
                    </div>
                    <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 4 }}>
                      每月用量：{quota.usedCount ?? 0}/{quota.monthlyLimit}，剩餘{" "}
                      {quota.remaining ?? "-"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <Panel title={`委託單列表（${filteredOrders.length} / ${orders.length} 筆）`}>
            <div
              style={{
                display: "flex",
                gap: 8,
                marginBottom: 16,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <button type="button" onClick={openCreateOrder} style={buttonStyle("green")}>
                新增委託單
              </button>

              <button type="button" onClick={() => void loadOrders()} style={buttonStyle("blue")}>
                重新整理列表
              </button>

              <Link href="/orders/templates" style={{ textDecoration: "none" }}>
                <span style={{ ...buttonStyle("gray"), display: "inline-flex" }}>管理模板</span>
              </Link>
            </div>

            <div style={filterTabsStyle}>
              {orderStatusFilters.map((filter) => (
                <button
                  key={filter.value}
                  type="button"
                  onClick={() => setActiveStatusFilter(filter.value)}
                  style={filterTabStyle(activeStatusFilter === filter.value)}
                >
                  {filter.label}
                  <span style={filterCountStyle}>{statusCounts[filter.value]}</span>
                </button>
              ))}
            </div>

            {loading ? (
              <div style={emptyStyle}>載入中...</div>
            ) : filteredOrders.length === 0 ? (
              <div style={emptyStyle}>目前沒有符合此分類的委託單</div>
            ) : (
              <div style={{ display: "grid", gap: 12 }}>
                {filteredOrders.map((order) => (
                  <div key={order.id} style={orderCardStyle}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                      <div>
                        <div style={{ fontWeight: 800, fontFamily: "monospace" }}>
                          {order.orderNo}
                        </div>
                        <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
                          申請人：{order.applicantId}｜部門：{order.departmentId}｜項目數：
                          {order.totalItems}
                        </div>
                        <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
                          優先程度：{priorityLabel[order.priority || "normal"]}｜申請日期：
                          {formatDate(order.applyDate)}
                        </div>
                      </div>
                      <StatusBadge status={order.status} />
                    </div>

                    {order.lastReason && (
                      <div style={reasonBoxStyle}>最近原因：{order.lastReason}</div>
                    )}

                    {order.items && order.items.length > 0 && (
                      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                        {order.items.map((item, index) => {
                          const itemStatus = getEffectiveItemStatus(order, item);

                          return (
                            <div key={item.id || index} style={orderItemStatusStyle}>
                              <div
                                style={{ display: "flex", justifyContent: "space-between", gap: 8 }}
                              >
                                <strong>
                                  子單 {index + 1}｜{item.labId}
                                </strong>
                                <span>{statusLabel[itemStatus as OrderStatus] || itemStatus}</span>
                              </div>
                              <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 4 }}>
                                樣品：{item.sampleId}｜實驗：{item.experimentId}
                                {item.approvedBy && `｜核准：${item.approvedBy}`}
                                {item.returnReason && `｜退回：${item.returnReason}`}
                                {item.rejectReason && `｜拒絕：${item.rejectReason}`}
                                {item.quotaExceeded && "｜配額超額"}
                                {item.quotaOverride && "｜已特批"}
                              </div>
                              <div
                                style={{
                                  color: item.quotaExceeded ? "#ffd28a" : "var(--green)",
                                  fontSize: 12,
                                  marginTop: 4,
                                }}
                              >
                                {quotaStatusText(item)}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
                      <button
                        type="button"
                        onClick={() => void getDetail(order.id)}
                        style={buttonStyle("gray")}
                      >
                        詳細
                      </button>
                      <button
                        type="button"
                        onClick={() => void getHistory(order.id)}
                        style={buttonStyle("gray")}
                      >
                        歷程
                      </button>

                      {(order.status === "draft" || order.status === "returned") && (
                        <button
                          type="button"
                          onClick={() => startEditOrder(order)}
                          style={buttonStyle("green")}
                        >
                          {order.status === "returned" ? "修改補件" : "修改草稿"}
                        </button>
                      )}

                      {allowedActions[order.status].map((action) => (
                        <button
                          key={action}
                          type="button"
                          onClick={() => void doAction(order, action)}
                          style={buttonStyle(action === "cancel" ? "red" : "blue")}
                        >
                          {actionLabel[action]}
                        </button>
                      ))}

                      {order.status === "draft" && (
                        <button
                          type="button"
                          onClick={() => void deleteOrder(order)}
                          style={buttonStyle("red")}
                        >
                          刪除
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      {formModalOpen && (
        <Modal
          title={editingOrderId ? "修改委託單 " + (editingOrderNo || "") : "新增委託單"}
          onClose={closeFormModal}
        >
          {orderForm}
        </Modal>
      )}

      {modal.type !== "none" && (
        <Modal title={modal.title} onClose={() => setModal({ type: "none" })}>
          {modal.type === "message" && (
            <p style={{ color: "var(--text2)", lineHeight: 1.8 }}>{modal.message}</p>
          )}

          {modal.type === "detail" && <OrderDetail order={modal.order} />}

          {modal.type === "history" && <HistoryTimeline history={modal.history} />}
        </Modal>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block", marginTop: 10 }}>
      <div style={{ fontSize: 12, color: "var(--text3)", marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}

function Input({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <input
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      style={{
        ...inputStyle,
        opacity: disabled ? 0.65 : 1,
        cursor: disabled ? "not-allowed" : "text",
      }}
    />
  );
}

function StatusBadge({ status }: { status: OrderStatus }) {
  return <span style={statusBadgeStyle}>{statusLabel[status]}</span>;
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div style={modalOverlayStyle}>
      <div style={modalStyle}>
        <div style={modalHeaderStyle}>
          <h3 style={{ margin: 0, fontSize: 17 }}>{title}</h3>
          <button type="button" onClick={onClose} style={buttonStyle("red")}>
            關閉
          </button>
        </div>

        <div style={{ padding: 18, overflowY: "auto" }}>{children}</div>
      </div>
    </div>
  );
}

function OrderDetail({ order }: { order: Order }) {
  return (
    <div>
      <div style={infoCardStyle}>
        <h4 style={cardTitleStyle}>委託單基本資料</h4>
        <InfoGrid
          rows={[
            ["委託單編號", order.orderNo],
            ["目前狀態", statusLabel[order.status]],
            ["申請人", order.applicantId],
            ["部門 / 廠區", order.departmentId],
            ["優先程度", priorityLabel[order.priority || "normal"]],
            ["申請日期", formatDate(order.applyDate)],
            ["實驗明細數量", `${order.totalItems} 筆`],
            ["最近原因", order.lastReason || "-"],
            ["建立時間", formatDate(order.createdAt)],
            ["更新時間", formatDate(order.updatedAt)],
          ]}
        />
      </div>

      <div style={infoCardStyle}>
        <h4 style={cardTitleStyle}>實驗明細</h4>
        {!order.items || order.items.length === 0 ? (
          <div style={emptyStyle}>目前沒有實驗明細資料</div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {order.items.map((item, index) => (
              <div key={item.id || index} style={itemCardStyle}>
                <InfoGrid
                  rows={[
                    ["序號", `子單 ${index + 1}`],
                    ["樣品編號", item.sampleId],
                    ["實驗室", item.labId],
                    ["實驗項目", item.experimentId],
                    [
                      "明細狀態",
                      statusLabel[getEffectiveItemStatus(order, item) as OrderStatus] ||
                        getEffectiveItemStatus(order, item),
                    ],
                    ["核准主管", item.approvedBy || "-"],
                    ["核准時間", item.approvedAt ? formatDate(item.approvedAt) : "-"],
                    ["配額狀態", quotaStatusText(item)],
                    ["配額超額", item.quotaExceeded ? "是" : "否"],
                    ["特批核准", item.quotaOverride ? "是" : "否"],
                    ["退回原因", item.returnReason || "-"],
                    ["拒絕原因", item.rejectReason || "-"],
                  ]}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function HistoryTimeline({ history }: { history: OrderHistory[] }) {
  if (history.length === 0) {
    return <div style={emptyStyle}>目前沒有流程歷程資料</div>;
  }

  return (
    <div style={{ borderLeft: "3px solid var(--border)", paddingLeft: 16 }}>
      {history.map((item, index) => (
        <div key={item.id || index} style={timelineItemStyle}>
          <div style={{ fontWeight: 800, color: "var(--text)" }}>
            {index + 1}. {item.action}
          </div>
          <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
            操作人：{item.actorId}｜時間：{formatDate(item.actionTime)}
          </div>
          <div style={{ marginTop: 8 }}>
            <InfoGrid
              rows={[
                [
                  "原狀態",
                  item.fromStatus
                    ? statusLabel[item.fromStatus as OrderStatus] || item.fromStatus
                    : "-",
                ],
                ["新狀態", statusLabel[item.toStatus as OrderStatus] || item.toStatus],
                ["特批", item.quotaOverride ? "是" : "否"],
                ["原因", item.reason || "-"],
              ]}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function InfoGrid({ rows }: { rows: [string, string][] }) {
  return (
    <div
      style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "8px 12px", fontSize: 13 }}
    >
      {rows.map(([label, value]) => (
        <div key={label} style={{ display: "contents" }}>
          <div style={{ color: "var(--text3)", fontWeight: 700 }}>{label}</div>
          <div style={{ color: "var(--text)" }}>{value || "-"}</div>
        </div>
      ))}
    </div>
  );
}

const orderWorkspaceGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "320px minmax(0, 1fr)",
  alignItems: "start",
  gap: 16,
};

const quotaSummaryStyle: CSSProperties = {
  position: "relative",
  background: "linear-gradient(135deg, rgba(56,139,253,.16), var(--s1))",
  border: "1px solid rgba(56,139,253,.35)",
  borderRadius: 12,
  padding: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,.18)",
};

const summaryTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 16,
  fontWeight: 800,
};

const summaryTextStyle: CSSProperties = {
  color: "var(--text3)",
  fontSize: 12,
  margin: "6px 0 0",
};

const quotaSummaryItemStyle: CSSProperties = {
  background: "rgba(13, 17, 23, .46)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 10,
};

const quotaDetailListStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  marginTop: 14,
};

const filterTabsStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 8,
  marginBottom: 14,
};

function filterTabStyle(active: boolean): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    background: active ? "var(--blue)" : "var(--s2)",
    border: active ? "1px solid var(--blue)" : "1px solid var(--border2)",
    borderRadius: 999,
    color: active ? "#fff" : "var(--text2)",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 800,
    padding: "7px 10px",
  };
}

const filterCountStyle: CSSProperties = {
  background: "rgba(255,255,255,.14)",
  borderRadius: 999,
  padding: "1px 6px",
};

const panelStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,.18)",
};

const panelTitleStyle: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 16,
  fontWeight: 800,
};

const inputStyle: CSSProperties = {
  width: "100%",
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: "9px 10px",
  outline: "none",
};

const orderCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  padding: 14,
};

const itemCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 12,
};

const experimentChecklistStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  marginTop: 12,
};

const experimentLabGroupStyle: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 10,
};

const checkboxRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  color: "var(--text2)",
  fontSize: 12,
};

const editNoticeStyle: CSSProperties = {
  padding: 10,
  borderRadius: 8,
  background: "rgba(245, 158, 11, .12)",
  border: "1px solid rgba(245, 158, 11, .35)",
  color: "var(--text2)",
  fontSize: 12,
  marginBottom: 12,
};

const templateBoxStyle: CSSProperties = {
  background: "rgba(56,139,253,.08)",
  border: "1px solid rgba(56,139,253,.28)",
  borderRadius: 10,
  padding: 12,
  marginTop: 12,
};

const statusBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: 999,
  background: "rgba(56,139,253,.18)",
  color: "var(--blue)",
  fontSize: 11,
  fontWeight: 800,
  padding: "4px 8px",
  height: 24,
  whiteSpace: "nowrap",
};

const emptyStyle: CSSProperties = {
  padding: 18,
  textAlign: "center",
  color: "var(--text3)",
  border: "1px dashed var(--border)",
  borderRadius: 10,
  background: "var(--s2)",
};

const reasonBoxStyle: CSSProperties = {
  marginTop: 10,
  padding: 10,
  borderRadius: 8,
  background: "rgba(245, 158, 11, .12)",
  border: "1px solid rgba(245, 158, 11, .35)",
  color: "var(--text2)",
  fontSize: 12,
};

const orderItemStatusStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 10,
};

const quotaBoxStyle: CSSProperties = {
  marginTop: 12,
  padding: 10,
  borderRadius: 8,
  background: "rgba(56,139,253,.12)",
  border: "1px solid rgba(56,139,253,.35)",
  color: "var(--text)",
};

const modalOverlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,.58)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
  zIndex: 50,
};

const modalStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 14,
  width: "min(900px, 94vw)",
  maxHeight: "86vh",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

const modalHeaderStyle: CSSProperties = {
  padding: "14px 18px",
  borderBottom: "1px solid var(--border2)",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
};

const infoCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  padding: 14,
  marginBottom: 12,
};

const timelineItemStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 12,
  marginBottom: 12,
};

const cardTitleStyle: CSSProperties = {
  margin: "0 0 10px",
  fontSize: 15,
  fontWeight: 800,
};

function buttonStyle(kind: "blue" | "green" | "gray" | "red"): CSSProperties {
  const colors = {
    blue: "var(--blue)",
    green: "var(--green)",
    gray: "var(--s3)",
    red: "var(--red)",
  };

  return {
    background: colors[kind],
    color: kind === "gray" ? "var(--text2)" : "#fff",
    border: "1px solid var(--border)",
    borderRadius: 7,
    padding: "7px 10px",
    cursor: "pointer",
    fontSize: 12,
  };
}
