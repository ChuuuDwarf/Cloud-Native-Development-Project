"use client";

import type { Order, OrderAction, OrderItem, OrderStatus } from "../types";
import type { MasterData } from "@/services/master-data-api";
import {
  displayDepartmentName,
  displayExperimentName,
  displayLabName,
  displayUserName,
} from "@/lib/displayNames";
import {
  approvableItemsForActor,
  canActorApproveItem,
  getEffectiveItemStatus,
  isHighPriority,
  itemNeedsQuotaOverride,
  quotaStatusText,
} from "../lib/approvalRules";
import { formatDate } from "../lib/format";
import { priorityLabel, statusLabel } from "../lib/labels";
import {
  approvalCardStyle,
  approvableItemStyle,
  buttonStyle,
  itemApprovalStyle,
  priorityCardStyle,
  quotaExceededStyle,
  quotaNormalStyle,
  quotaOverrideOkStyle,
  reasonBoxStyle,
} from "../styles";
import { PriorityBadge, StatusBadge } from "./Badges";

type OrderCardProps = {
  order: Order;
  actorLabIds: string[];
  masterData: Pick<MasterData, "departments" | "labs" | "experiments">;
  usersById: Record<string, string | undefined>;
  currentUser: { id: string; name: string } | null;
  onOpenDetail: (orderId: number) => void;
  onOpenHistory: (orderId: number) => void;
  onOpenReasonModal: (
    order: Order,
    action: OrderAction,
    orderItem?: OrderItem,
    forceQuotaOverride?: boolean
  ) => void;
};

export function OrderCard({
  order,
  actorLabIds,
  masterData,
  usersById,
  currentUser,
  onOpenDetail,
  onOpenHistory,
  onOpenReasonModal,
}: OrderCardProps) {
  const approvableItems = approvableItemsForActor(actorLabIds, order);

  return (
    <div
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
            style={{ fontFamily: "monospace", color: "var(--text)", fontWeight: 800, fontSize: 14 }}
          >
            {order.orderNo}
          </div>

          <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
            申請人：{displayUserName(order.applicantId, usersById, currentUser)} ｜ 部門：
            {displayDepartmentName(masterData, order.departmentId)} ｜ 項目數：{order.totalItems}
          </div>

          <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
            優先程度：{priorityLabel[order.priority || "normal"]} ｜ 申請日期：
            {formatDate(order.applyDate)}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
          <PriorityBadge priority={order.priority || "normal"} />
          <StatusBadge status={order.status} />
        </div>
      </div>

      {order.lastReason && <div style={reasonBoxStyle}>最近原因：{order.lastReason}</div>}

      {order.items && order.items.length > 0 && (
        <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
          {order.items.map((item, index) => (
            <OrderItemApprovalCard
              key={item.id || index}
              index={index}
              item={item}
              order={order}
              actorLabIds={actorLabIds}
              masterData={masterData}
              usersById={usersById}
              currentUser={currentUser}
              onOpenReasonModal={onOpenReasonModal}
            />
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
        <button type="button" onClick={() => onOpenDetail(order.id)} style={buttonStyle("gray")}>
          查看詳細
        </button>

        <button type="button" onClick={() => onOpenHistory(order.id)} style={buttonStyle("gray")}>
          查看歷程
        </button>

        {approvableItems.length > 0 && (
          <>
            <button
              type="button"
              onClick={() =>
                onOpenReasonModal(
                  order,
                  "approve",
                  undefined,
                  approvableItems.some((item) => itemNeedsQuotaOverride(order, item))
                )
              }
              style={buttonStyle("green")}
            >
              核准所有
            </button>

            <button
              type="button"
              onClick={() => onOpenReasonModal(order, "return")}
              style={buttonStyle("blue")}
            >
              退回所有
            </button>

            <button
              type="button"
              onClick={() => onOpenReasonModal(order, "reject")}
              style={buttonStyle("red")}
            >
              拒絕所有
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function OrderItemApprovalCard({
  order,
  item,
  index,
  actorLabIds,
  masterData,
  usersById,
  currentUser,
  onOpenReasonModal,
}: {
  order: Order;
  item: OrderItem;
  index: number;
  actorLabIds: string[];
  masterData: Pick<MasterData, "departments" | "labs" | "experiments">;
  usersById: Record<string, string | undefined>;
  currentUser: { id: string; name: string } | null;
  onOpenReasonModal: OrderCardProps["onOpenReasonModal"];
}) {
  const canApproveItem = canActorApproveItem(actorLabIds, order, item);
  const needsQuotaOverride = itemNeedsQuotaOverride(order, item);
  const effectiveStatus = getEffectiveItemStatus(order, item);

  return (
    <div style={canApproveItem ? approvableItemStyle : itemApprovalStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <strong>
          明細 {index + 1}｜{displayLabName(masterData, item.labId)}
        </strong>
        <span>{statusLabel[effectiveStatus as OrderStatus] || effectiveStatus}</span>
      </div>

      <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 4 }}>
        樣品：{item.sampleId}｜實驗：{displayExperimentName(masterData, item.experimentId)}
        {item.approvedBy && `｜核准：${displayUserName(item.approvedBy, usersById, currentUser)}`}
        {item.returnReason && `｜退回：${item.returnReason}`}
        {item.rejectReason && `｜拒絕：${item.rejectReason}`}
      </div>

      <div
        style={
          item.quotaOverride
            ? quotaOverrideOkStyle
            : needsQuotaOverride
              ? quotaExceededStyle
              : quotaNormalStyle
        }
      >
        {quotaStatusText(order, item)}
      </div>

      {(needsQuotaOverride || item.quotaOverride) && (
        <div style={item.quotaOverride ? quotaOverrideOkStyle : quotaExceededStyle}>
          {item.quotaOverride ? "已特批" : "此子單超額，需主管特批後才能核准"}
        </div>
      )}

      <div
        style={{
          color: canApproveItem ? "var(--green)" : "var(--text3)",
          fontSize: 12,
          marginTop: 8,
        }}
      >
        {canApproveItem
          ? "可簽核：此明細屬於目前主管實驗室"
          : "僅可查看：此明細不屬於目前主管，或已完成簽核"}
      </div>

      {canApproveItem && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {needsQuotaOverride ? (
            <button
              type="button"
              onClick={() => onOpenReasonModal(order, "approve", item, true)}
              style={buttonStyle("green")}
            >
              特批核准
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onOpenReasonModal(order, "approve", item)}
              style={buttonStyle("green")}
            >
              核准
            </button>
          )}
          <button
            type="button"
            onClick={() => onOpenReasonModal(order, "return", item)}
            style={buttonStyle("blue")}
          >
            退回
          </button>
          <button
            type="button"
            onClick={() => onOpenReasonModal(order, "reject", item)}
            style={buttonStyle("red")}
          >
            拒絕
          </button>
        </div>
      )}
    </div>
  );
}
