import { priorityLabel, statusLabel } from "../constants";
import { cardTitleStyle, emptyStyle, infoCardStyle, itemCardStyle } from "../styles";
import type { MasterData, Order, OrderStatus, UserNameLookup } from "../types";
import { formatDate, getEffectiveItemStatus, quotaStatusText } from "../lib/format";
import {
  displayDepartmentName,
  displayExperimentName,
  displayLabName,
  displayUserName,
} from "@/lib/displayNames";
import { InfoGrid } from "./common";

export function OrderDetail({
  order,
  masterData,
  currentUser,
  usersById,
}: {
  order: Order;
  masterData: MasterData;
  currentUser: { id: string; name: string };
  usersById: UserNameLookup;
}) {
  return (
    <div>
      <div style={infoCardStyle}>
        <h4 style={cardTitleStyle}>委託單基本資料</h4>
        <InfoGrid
          rows={[
            ["委託單編號", order.orderNo],
            ["目前狀態", statusLabel[order.status]],
            ["申請人", displayUserName(order.applicantId, usersById, currentUser)],
            ["部門 / 廠區", displayDepartmentName(masterData, order.departmentId)],
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
                    ["實驗室", displayLabName(masterData, item.labId)],
                    ["實驗項目", displayExperimentName(masterData, item.experimentId)],
                    [
                      "明細狀態",
                      statusLabel[getEffectiveItemStatus(order, item) as OrderStatus] ||
                        getEffectiveItemStatus(order, item),
                    ],
                    ["核准主管", displayUserName(item.approvedBy, usersById, currentUser)],
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
