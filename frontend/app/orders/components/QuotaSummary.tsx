import {
  buttonStyle,
  quotaDetailListStyle,
  quotaSummaryItemStyle,
  quotaSummaryStyle,
  summaryTextStyle,
  summaryTitleStyle,
} from "../styles";
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
  currentUser: {
    id: string;
    name: string;
    role?: string;
    departmentId?: string | null;
  };
  onRefresh: () => void;
}) {
  const filteredQuotaSettings =
    currentUser.role === "plant_user"
      ? quotaSettings.filter((quota) => {
          if (quota.scopeType === "user") {
            return quota.scopeId === currentUser.id;
          }

          if (quota.scopeType === "department") {
            return quota.scopeId === currentUser.departmentId;
          }

          return false;
        })
      : quotaSettings;

  const sortedQuotaSettings = [...filteredQuotaSettings].sort((a, b) => {
    const order: Record<string, number> = {
      user: 0,
      department: 1,
    };

    return (order[a.scopeType] ?? 99) - (order[b.scopeType] ?? 99);
  });

  return (
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
          <p style={summaryTextStyle}>
            {currentUser.role === "plant_user"
              ? "顯示個人與所屬部門配額明細"
              : "顯示個人與部門配額明細"}
          </p>
        </div>

        <button type="button" onClick={onRefresh} style={buttonStyle("blue")}>
          更新
        </button>
      </div>

      {sortedQuotaSettings.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 12 }}>
          目前沒有配額資料
        </div>
      ) : (
        <div style={quotaDetailListStyle}>
          {sortedQuotaSettings.map((quota) => (
            <div key={quota.id} style={quotaSummaryItemStyle}>
              <div style={{ fontWeight: 800 }}>
                {quota.scopeType === "user"
                  ? "個人"
                  : quota.scopeType === "department"
                    ? "部門"
                    : quota.scopeType}
                ：
                {displayScopeName(
                  masterData,
                  usersById,
                  quota.scopeType,
                  quota.scopeId,
                  currentUser,
                )}
              </div>

              <div
                style={{
                  color: "var(--text2)",
                  fontSize: 12,
                  marginTop: 4,
                }}
              >
                每月用量：{quota.effectiveUsedCount ?? ((quota.usedCount ?? 0) + (quota.reservedCount ?? 0))}/{quota.monthlyLimit}
                {quota.reservedCount ? `，待簽核保留 ${quota.reservedCount}` : ""}
                ，剩餘 {quota.remaining ?? "-"}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}