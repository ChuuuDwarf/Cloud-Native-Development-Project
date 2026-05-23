import { buttonStyle, quotaDetailListStyle, quotaSummaryItemStyle, quotaSummaryStyle, summaryTextStyle, summaryTitleStyle } from "../styles";
import type { MasterData, QuotaSetting, UserNameLookup } from "../types";
import { displayScopeName } from "@/lib/displayNames";

export function QuotaSummary({
  quotaSettings,
  masterData,
  usersById,
  currentUser,
  onRefresh,
}: {
  quotaSettings: QuotaSetting[];
  masterData: MasterData;
  usersById: UserNameLookup;
  currentUser: { id: string; name: string };
  onRefresh: () => void;
}) {
  return (
    <section style={quotaSummaryStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div>
          <h2 style={summaryTitleStyle}>配額用量</h2>
          <p style={summaryTextStyle}>顯示個人與部門配額明細</p>
        </div>
        <button type="button" onClick={onRefresh} style={buttonStyle("blue")}>更新</button>
      </div>

      {quotaSettings.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 12 }}>目前沒有配額資料</div>
      ) : (
        <div style={quotaDetailListStyle}>
          {quotaSettings.map((quota) => (
            <div key={quota.id} style={quotaSummaryItemStyle}>
              <div style={{ fontWeight: 800 }}>{quota.scopeType === "user" ? "個人" : quota.scopeType === "department" ? "部門" : quota.scopeType}：{displayScopeName(masterData, usersById, quota.scopeType, quota.scopeId, currentUser)}</div>
              <div style={{ color: "var(--text2)", fontSize: 12, marginTop: 4 }}>每月用量：{quota.usedCount ?? 0}/{quota.monthlyLimit}，剩餘 {quota.remaining ?? "-"}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
