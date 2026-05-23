import Link from "next/link";
import { actionLabel, allowedActions, orderStatusFilters, priorityLabel, statusLabel } from "../constants";
import { buttonStyle, emptyStyle, filterCountStyle, filterTabsStyle, filterTabStyle, orderCardStyle, orderItemStatusStyle, reasonBoxStyle } from "../styles";
import type { MasterData, Order, OrderAction, OrderStatus, OrderStatusFilter, UserNameLookup } from "../types";
import { formatDate, getEffectiveItemStatus, quotaStatusText } from "../lib/format";
import { displayDepartmentName, displayExperimentName, displayLabName, displayUserName } from "@/lib/displayNames";
import { Panel, StatusBadge } from "./common";

export function OrderList({
  orders,
  filteredOrders,
  masterData,
  currentUser,
  usersById,
  loading,
  activeStatusFilter,
  statusCounts,
  onFilterChange,
  onCreate,
  onRefresh,
  onDetail,
  onHistory,
  onEdit,
  onAction,
  onDelete,
}: {
  orders: Order[];
  filteredOrders: Order[];
  masterData: MasterData;
  currentUser: { id: string; name: string };
  usersById: UserNameLookup;
  loading: boolean;
  activeStatusFilter: OrderStatusFilter;
  statusCounts: Record<OrderStatusFilter, number>;
  onFilterChange: (filter: OrderStatusFilter) => void;
  onCreate: () => void;
  onRefresh: () => void;
  onDetail: (orderId: number) => void;
  onHistory: (orderId: number) => void;
  onEdit: (order: Order) => void;
  onAction: (order: Order, action: OrderAction) => void;
  onDelete: (order: Order) => void;
}) {
  return (
    <Panel title={`委託單列表（${filteredOrders.length} / ${orders.length} 筆）`}>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <button type="button" onClick={onCreate} style={buttonStyle("green")}>新增委託單</button>
        <button type="button" onClick={onRefresh} style={buttonStyle("blue")}>重新整理列表</button>
        <Link href="/orders/templates" style={{ textDecoration: "none" }}>
          <span style={{ ...buttonStyle("gray"), display: "inline-flex" }}>管理模板</span>
        </Link>
      </div>

      <div style={filterTabsStyle}>
        {orderStatusFilters.map((filter) => (
          <button key={filter.value} type="button" onClick={() => onFilterChange(filter.value)} style={filterTabStyle(activeStatusFilter === filter.value)}>
            {filter.label}<span style={filterCountStyle}>{statusCounts[filter.value]}</span>
          </button>
        ))}
      </div>

      {loading ? <div style={emptyStyle}>載入中...</div> : filteredOrders.length === 0 ? <div style={emptyStyle}>目前沒有符合此分類的委託單</div> : (
        <div style={{ display: "grid", gap: 12 }}>
          {filteredOrders.map((order) => (
            <div key={order.id} style={orderCardStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <div style={{ fontWeight: 800, fontFamily: "monospace" }}>{order.orderNo}</div>
                  <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>申請人：{displayUserName(order.applicantId, usersById, currentUser)}｜部門：{displayDepartmentName(masterData, order.departmentId)}｜項目數：{order.totalItems}</div>
                  <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>優先程度：{priorityLabel[order.priority || "normal"]}｜申請日期：{formatDate(order.applyDate)}</div>
                </div>
                <StatusBadge status={order.status} />
              </div>

              {order.lastReason && <div style={reasonBoxStyle}>最近原因：{order.lastReason}</div>}

              {order.items && order.items.length > 0 && (
                <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                  {order.items.map((item, index) => {
                    const itemStatus = getEffectiveItemStatus(order, item);
                    return (
                      <div key={item.id || index} style={orderItemStatusStyle}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                          <strong>子單 {index + 1}｜{displayLabName(masterData, item.labId)}</strong>
                          <span>{statusLabel[itemStatus as OrderStatus] || itemStatus}</span>
                        </div>
                        <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 4 }}>
                          樣品：{item.sampleId}｜實驗：{displayExperimentName(masterData, item.experimentId)}
                          {item.approvedBy && `｜核准：${displayUserName(item.approvedBy, usersById, currentUser)}`}
                          {item.returnReason && `｜退回：${item.returnReason}`}
                          {item.rejectReason && `｜拒絕：${item.rejectReason}`}
                          {item.quotaExceeded && "｜配額超額"}
                          {item.quotaOverride && "｜已特批"}
                        </div>
                        <div style={{ color: item.quotaExceeded ? "#ffd28a" : "var(--green)", fontSize: 12, marginTop: 4 }}>{quotaStatusText(item)}</div>
                      </div>
                    );
                  })}
                </div>
              )}

              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
                <button type="button" onClick={() => onDetail(order.id)} style={buttonStyle("gray")}>詳細</button>
                <button type="button" onClick={() => onHistory(order.id)} style={buttonStyle("gray")}>歷程</button>
                {(order.status === "draft" || order.status === "returned") && <button type="button" onClick={() => onEdit(order)} style={buttonStyle("green")}>{order.status === "returned" ? "修改補件" : "修改草稿"}</button>}
                {allowedActions[order.status].map((action) => <button key={action} type="button" onClick={() => onAction(order, action)} style={buttonStyle(action === "cancel" ? "red" : "blue")}>{actionLabel[action]}</button>)}
                {order.status === "draft" && <button type="button" onClick={() => onDelete(order)} style={buttonStyle("red")}>刪除</button>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
