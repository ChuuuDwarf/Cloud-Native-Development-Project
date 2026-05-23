"use client";

import { useEffect, useState } from "react";
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

type OrderAction = "approve" | "return" | "reject";

type PriorityLevel = "normal" | "urgent" | "critical";

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

type ModalState =
  | { type: "none" }
  | { type: "message"; title: string; message: string }
  | { type: "detail"; title: string; order: Order }
  | { type: "history"; title: string; history: OrderHistory[] };

type ReasonModalState =
  | { open: false }
  | {
      open: true;
      title: string;
      hint: string;
      action: OrderAction;
      order: Order;
      orderItem?: OrderItem;
      quotaOverride?: boolean;
      value: string;
    };

const approverOptions = [
  { id: "manager001", label: "manager001｜LAB001/LAB002 主管", labIds: ["LAB001", "LAB002"] },
  { id: "manager003", label: "manager003｜LAB003 主管", labIds: ["LAB003"] },
];

const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  approve: "核准",
  return: "退回補件",
  reject: "拒絕",
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "API request failed");
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

const priorityRank: Record<PriorityLevel, number> = {
  critical: 0,
  urgent: 1,
  normal: 2,
};

function sortApprovalOrders(items: Order[]) {
  return [...items].sort((a, b) => {
    const priorityDiff =
      priorityRank[a.priority || "normal"] - priorityRank[b.priority || "normal"];
    if (priorityDiff !== 0) return priorityDiff;
    return new Date(b.applyDate).getTime() - new Date(a.applyDate).getTime();
  });
}

function isHighPriority(priority?: PriorityLevel) {
  return priority === "critical" || priority === "urgent";
}

function getEffectiveItemStatus(order: Order, item: OrderItem) {
  if (order.status === "pending_approval" && (!item.status || item.status === "draft")) {
    return "pending_approval";
  }

  return item.status || "-";
}

function getApproverLabIds(actorId: string) {
  return approverOptions.find((option) => option.id === actorId)?.labIds || [];
}

function canActorApproveItem(actorId: string, order: Order, item: OrderItem) {
  return (
    order.status === "pending_approval" &&
    getApproverLabIds(actorId).includes(item.labId) &&
    getEffectiveItemStatus(order, item) === "pending_approval"
  );
}

function orderHasQuotaExceededReason(order: Order) {
  return Boolean(order.lastReason?.includes("配額") || order.lastReason?.includes("超額"));
}

function itemNeedsQuotaOverride(order: Order, item: OrderItem) {
  return !item.quotaOverride && (item.quotaExceeded ?? orderHasQuotaExceededReason(order));
}

function quotaStatusText(order: Order, item: OrderItem) {
  if (item.quotaOverride) return "配額：已特批";
  if (itemNeedsQuotaOverride(order, item)) return "配額：需特批";
  return "配額：正常";
}

function approvableItemsForActor(actorId: string, order: Order) {
  return (order.items || []).filter((item) => canActorApproveItem(actorId, order, item));
}

export default function ApprovePage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [actorId, setActorId] = useState("manager001");
  const [quotaOverride, setQuotaOverride] = useState(false);
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState("尚未執行任何動作");
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [reasonModal, setReasonModal] = useState<ReasonModalState>({ open: false });

  async function loadPendingOrders() {
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
  }

  async function getDetail(orderId: number) {
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
  }

  async function getHistory(orderId: number) {
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
  }

  function openReasonModal(
    order: Order,
    action: OrderAction,
    orderItem?: OrderItem,
    forceQuotaOverride = false
  ) {
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
  }

  async function submitAction(
    order: Order,
    action: OrderAction,
    reason?: string,
    orderItemId?: number,
    useQuotaOverride = quotaOverride
  ) {
    if (order.status !== "pending_approval") {
      setModal({
        type: "message",
        title: "無法執行簽核",
        message: `目前狀態為「${statusLabel[order.status]}」，只有「待簽核」狀態可以核准、退回或拒絕。`,
      });
      return;
    }

    const body: {
      action: OrderAction;
      actorId: string;
      orderItemId?: number;
      reason?: string;
      quotaOverride?: boolean;
    } = {
      action,
      actorId,
    };

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
  }

  function submitReasonModal() {
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
  }

  useEffect(() => {
    queueMicrotask(() => {
      void loadPendingOrders();
    });
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>簽核管理</h1>
        <p style={{ color: "var(--text3)", fontSize: 12, marginTop: 4, fontFamily: "monospace" }}>
          APPROVAL MANAGEMENT · 查看待簽核單據、核准、退回補件、拒絕與特批超額送測
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Panel title="簽核操作設定">
            <Field label="簽核人員 actorId">
              <select
                value={actorId}
                onChange={(event) => setActorId(event.target.value)}
                style={inputStyle}
              >
                {approverOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>

            <label
              style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12, fontSize: 13 }}
            >
              <input
                checked={quotaOverride}
                onChange={(event) => setQuotaOverride(event.target.checked)}
                type="checkbox"
              />
              <span>核准時使用 quotaOverride 特批超額送測</span>
            </label>

            <button
              type="button"
              onClick={() => void loadPendingOrders()}
              style={{ ...buttonStyle("blue"), width: "100%", marginTop: 12 }}
            >
              重新整理待簽核清單
            </button>
          </Panel>

          <Panel title="API 執行結果">
            <pre style={logStyle}>{log}</pre>
          </Panel>
        </div>

        <div>
          <Panel title={`待簽核委託單（${orders.length} 筆）`}>
            <p style={{ color: "var(--text2)", fontSize: 12, marginBottom: 12 }}>
              只有狀態為「待簽核」的委託單會出現在這裡。主管可進行核准、退回補件或拒絕。
            </p>

            {loading ? (
              <div style={emptyStyle}>載入中...</div>
            ) : orders.length === 0 ? (
              <div style={emptyStyle}>
                目前沒有待簽核委託單。請先到「委託單管理」建立草稿並送出。
              </div>
            ) : (
              <div style={{ display: "grid", gap: 12 }}>
                {orders.map((order) => (
                  <div
                    key={order.id}
                    style={
                      isHighPriority(order.priority)
                        ? { ...approvalCardStyle, ...priorityCardStyle(order.priority) }
                        : approvalCardStyle
                    }
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 12,
                        alignItems: "flex-start",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontFamily: "monospace",
                            color: "var(--text)",
                            fontWeight: 800,
                            fontSize: 14,
                          }}
                        >
                          {order.orderNo}
                        </div>

                        <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
                          申請人：{order.applicantId} ｜ 部門：{order.departmentId} ｜ 項目數：
                          {order.totalItems}
                        </div>

                        <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
                          優先程度：{priorityLabel[order.priority || "normal"]} ｜ 申請日期：
                          {formatDate(order.applyDate)}
                        </div>
                      </div>

                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "flex-end",
                          gap: 8,
                        }}
                      >
                        <PriorityBadge priority={order.priority || "normal"} />
                        <StatusBadge status={order.status} />
                      </div>
                    </div>

                    {order.lastReason && (
                      <div style={reasonBoxStyle}>最近原因：{order.lastReason}</div>
                    )}

                    {order.items && order.items.length > 0 && (
                      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                        {order.items.map((item, index) => (
                          <div
                            key={item.id || index}
                            style={
                              canActorApproveItem(actorId, order, item)
                                ? approvableItemStyle
                                : itemApprovalStyle
                            }
                          >
                            <div
                              style={{ display: "flex", justifyContent: "space-between", gap: 8 }}
                            >
                              <strong>
                                明細 {index + 1}｜{item.labId}
                              </strong>
                              <span>
                                {statusLabel[getEffectiveItemStatus(order, item) as OrderStatus] ||
                                  getEffectiveItemStatus(order, item)}
                              </span>
                            </div>
                            <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 4 }}>
                              樣品：{item.sampleId}｜實驗：{item.experimentId}
                              {item.approvedBy && `｜核准：${item.approvedBy}`}
                              {item.returnReason && `｜退回：${item.returnReason}`}
                              {item.rejectReason && `｜拒絕：${item.rejectReason}`}
                            </div>
                            <div
                              style={
                                item.quotaOverride
                                  ? quotaOverrideOkStyle
                                  : itemNeedsQuotaOverride(order, item)
                                    ? quotaExceededStyle
                                    : quotaNormalStyle
                              }
                            >
                              {quotaStatusText(order, item)}
                            </div>
                            {(itemNeedsQuotaOverride(order, item) || item.quotaOverride) && (
                              <div
                                style={
                                  item.quotaOverride ? quotaOverrideOkStyle : quotaExceededStyle
                                }
                              >
                                {item.quotaOverride ? "已特批" : "此子單超額，需主管特批後才能核准"}
                              </div>
                            )}
                            <div
                              style={{
                                color: canActorApproveItem(actorId, order, item)
                                  ? "var(--green)"
                                  : "var(--text3)",
                                fontSize: 12,
                                marginTop: 8,
                              }}
                            >
                              {canActorApproveItem(actorId, order, item)
                                ? "可簽核：此明細屬於目前主管實驗室"
                                : "僅可查看：此明細不屬於目前主管，或已完成簽核"}
                            </div>
                            {canActorApproveItem(actorId, order, item) && (
                              <div
                                style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}
                              >
                                {itemNeedsQuotaOverride(order, item) ? (
                                  <button
                                    type="button"
                                    onClick={() => openReasonModal(order, "approve", item, true)}
                                    style={buttonStyle("green")}
                                  >
                                    特批核准
                                  </button>
                                ) : (
                                  <button
                                    type="button"
                                    onClick={() => openReasonModal(order, "approve", item)}
                                    style={buttonStyle("green")}
                                  >
                                    核准
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => openReasonModal(order, "return", item)}
                                  style={buttonStyle("blue")}
                                >
                                  退回
                                </button>
                                <button
                                  type="button"
                                  onClick={() => openReasonModal(order, "reject", item)}
                                  style={buttonStyle("red")}
                                >
                                  拒絕
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
                      <button
                        type="button"
                        onClick={() => void getDetail(order.id)}
                        style={buttonStyle("gray")}
                      >
                        查看詳細
                      </button>

                      <button
                        type="button"
                        onClick={() => void getHistory(order.id)}
                        style={buttonStyle("gray")}
                      >
                        查看歷程
                      </button>

                      {approvableItemsForActor(actorId, order).length > 0 && (
                        <>
                          <button
                            type="button"
                            onClick={() =>
                              openReasonModal(
                                order,
                                "approve",
                                undefined,
                                approvableItemsForActor(actorId, order).some((item) =>
                                  itemNeedsQuotaOverride(order, item)
                                )
                              )
                            }
                            style={buttonStyle("green")}
                          >
                            核准所有
                          </button>

                          <button
                            type="button"
                            onClick={() => openReasonModal(order, "return")}
                            style={buttonStyle("blue")}
                          >
                            退回所有
                          </button>

                          <button
                            type="button"
                            onClick={() => openReasonModal(order, "reject")}
                            style={buttonStyle("red")}
                          >
                            拒絕所有
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      {modal.type !== "none" && (
        <Modal title={modal.title} onClose={() => setModal({ type: "none" })}>
          {modal.type === "message" && (
            <p style={{ color: "var(--text2)", lineHeight: 1.8 }}>{modal.message}</p>
          )}

          {modal.type === "detail" && <OrderDetail order={modal.order} />}

          {modal.type === "history" && <HistoryTimeline history={modal.history} />}
        </Modal>
      )}

      {reasonModal.open && (
        <Modal title={reasonModal.title} onClose={() => setReasonModal({ open: false })} narrow>
          <p style={{ color: "var(--text2)", fontSize: 13, lineHeight: 1.7, marginBottom: 12 }}>
            {reasonModal.hint}
          </p>

          <textarea
            value={reasonModal.value}
            onChange={(event) =>
              setReasonModal((current) =>
                current.open ? { ...current, value: event.target.value } : current
              )
            }
            placeholder="請輸入原因..."
            style={textareaStyle}
          />

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
            <button
              type="button"
              onClick={() => setReasonModal({ open: false })}
              style={buttonStyle("gray")}
            >
              取消
            </button>

            <button type="button" onClick={submitReasonModal} style={buttonStyle("blue")}>
              確認送出
            </button>
          </div>
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

function StatusBadge({ status }: { status: OrderStatus }) {
  return <span style={statusBadgeStyle}>{statusLabel[status] || status}</span>;
}

function PriorityBadge({ priority }: { priority: PriorityLevel }) {
  if (priority === "normal") return null;

  return (
    <span style={priorityBadgeStyle(priority)}>{priority === "critical" ? "特急件" : "急件"}</span>
  );
}

function Modal({
  title,
  children,
  onClose,
  narrow = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  narrow?: boolean;
}) {
  return (
    <div style={modalOverlayStyle}>
      <div style={{ ...modalStyle, width: narrow ? "min(520px, 92vw)" : "min(900px, 94vw)" }}>
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
            ["退回 / 拒絕原因", order.lastReason || "-"],
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
                    ["項次", `第 ${index + 1} 筆`],
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
            操作者：{item.actorId} ｜ 時間：{formatDate(item.actionTime)}
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

const textareaStyle: CSSProperties = {
  width: "100%",
  minHeight: 120,
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: 10,
  resize: "vertical",
  outline: "none",
};

const approvalCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 12,
  padding: 14,
};

function priorityCardStyle(priority?: PriorityLevel): CSSProperties {
  if (priority === "critical") {
    return {
      border: "1px solid rgba(248, 81, 73, .8)",
      boxShadow: "0 0 0 1px rgba(248, 81, 73, .18), 0 10px 30px rgba(248, 81, 73, .12)",
    };
  }

  if (priority === "urgent") {
    return {
      border: "1px solid rgba(245, 158, 11, .8)",
      boxShadow: "0 0 0 1px rgba(245, 158, 11, .18), 0 10px 30px rgba(245, 158, 11, .10)",
    };
  }

  return {};
}

const statusBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: 999,
  background: "rgba(56,139,253,.18)",
  color: "var(--blue)",
  fontSize: 11,
  fontWeight: 800,
  padding: "4px 8px",
  whiteSpace: "nowrap",
};

function priorityBadgeStyle(priority: PriorityLevel): CSSProperties {
  const isCritical = priority === "critical";

  return {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 999,
    background: isCritical ? "rgba(248, 81, 73, .22)" : "rgba(245, 158, 11, .22)",
    border: isCritical ? "1px solid rgba(248, 81, 73, .55)" : "1px solid rgba(245, 158, 11, .55)",
    color: isCritical ? "#ffb4ad" : "#ffd28a",
    fontSize: 11,
    fontWeight: 900,
    padding: "4px 8px",
    whiteSpace: "nowrap",
  };
}

const logStyle: CSSProperties = {
  background: "#05070a",
  border: "1px solid var(--border2)",
  borderRadius: 8,
  padding: 10,
  minHeight: 160,
  maxHeight: 260,
  overflow: "auto",
  color: "#a6e3a1",
  fontSize: 11,
  whiteSpace: "pre-wrap",
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

const quotaExceededStyle: CSSProperties = {
  marginTop: 8,
  padding: 8,
  borderRadius: 8,
  background: "rgba(245, 158, 11, .12)",
  border: "1px solid rgba(245, 158, 11, .35)",
  color: "#ffd28a",
  fontSize: 12,
};

const quotaNormalStyle: CSSProperties = {
  marginTop: 8,
  padding: 8,
  borderRadius: 8,
  background: "rgba(63, 185, 80, .08)",
  border: "1px solid rgba(63, 185, 80, .24)",
  color: "var(--green)",
  fontSize: 12,
};

const quotaOverrideOkStyle: CSSProperties = {
  ...quotaExceededStyle,
  background: "rgba(63, 185, 80, .12)",
  border: "1px solid rgba(63, 185, 80, .35)",
  color: "var(--green)",
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

const itemCardStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderLeft: "4px solid var(--blue)",
  borderRadius: 10,
  padding: 12,
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

const itemApprovalStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 10,
};

const approvableItemStyle: CSSProperties = {
  ...itemApprovalStyle,
  border: "1px solid rgba(63, 185, 80, .65)",
  boxShadow: "0 0 0 1px rgba(63, 185, 80, .12)",
};
