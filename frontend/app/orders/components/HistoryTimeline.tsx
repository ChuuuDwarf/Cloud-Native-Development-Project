import { statusLabel } from "../constants";
import { emptyStyle, timelineItemStyle } from "../styles";
import type { OrderHistory, OrderStatus, UserNameLookup } from "../types";
import { formatDate } from "../lib/format";
import { displayUserName } from "@/lib/displayNames";
import { InfoGrid } from "./common";

export function HistoryTimeline({
  history,
  usersById,
  currentUser,
}: {
  history: OrderHistory[];
  usersById: UserNameLookup;
  currentUser: { id: string; name: string };
}) {
  if (history.length === 0) return <div style={emptyStyle}>目前沒有流程歷程資料</div>;

  return (
    <div style={{ borderLeft: "3px solid var(--border)", paddingLeft: 16 }}>
      {history.map((item, index) => (
        <div key={item.id || index} style={timelineItemStyle}>
          <div style={{ fontWeight: 800, color: "var(--text)" }}>{index + 1}. {item.action}</div>
          <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 6 }}>
            操作人：{displayUserName(item.actorId, usersById, currentUser)}｜時間：{formatDate(item.actionTime)}
          </div>
          <div style={{ marginTop: 8 }}>
            <InfoGrid rows={[
              ["原狀態", item.fromStatus ? statusLabel[item.fromStatus as OrderStatus] || item.fromStatus : "-"],
              ["新狀態", statusLabel[item.toStatus as OrderStatus] || item.toStatus],
              ["特批", item.quotaOverride ? "是" : "否"],
              ["原因", item.reason || "-"],
            ]} />
          </div>
        </div>
      ))}
    </div>
  );
}
