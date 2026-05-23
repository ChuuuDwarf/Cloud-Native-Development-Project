"use client";

import { Field } from "./Field";
import { Panel } from "./Panel";
import { buttonStyle, inputStyle } from "../styles";
import type { MasterData } from "@/services/master-data-api";
import { displayLabName } from "@/lib/displayNames";

type ApprovalSettingsPanelProps = {
  userLabel: string;
  actorLabIds: string[];
  masterData: Pick<MasterData, "departments" | "labs" | "experiments">;
  canApprove: boolean;
  quotaOverride: boolean;
  onQuotaOverrideChange: (value: boolean) => void;
  onReload: () => void;
};

export function ApprovalSettingsPanel({
  userLabel,
  actorLabIds,
  masterData,
  canApprove,
  quotaOverride,
  onQuotaOverrideChange,
  onReload,
}: ApprovalSettingsPanelProps) {
  return (
    <Panel title="簽核操作設定">
      <Field label="目前簽核人員">
        <input value={userLabel} readOnly disabled style={inputStyle} />
      </Field>

      <Field label="可簽核實驗室">
        <input
          value={
            actorLabIds.length > 0
              ? actorLabIds.map((labId) => displayLabName(masterData, labId)).join(", ")
              : "尚無可簽核實驗室"
          }
          readOnly
          disabled
          style={inputStyle}
        />
      </Field>

      {!canApprove && (
        <div style={{ color: "#ffd28a", fontSize: 12, lineHeight: 1.7, marginTop: 10 }}>
          目前帳號沒有 orders:approve 權限，僅能查看待簽核資料。
        </div>
      )}

      <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12, fontSize: 13 }}>
        <input
          checked={quotaOverride}
          onChange={(event) => onQuotaOverrideChange(event.target.checked)}
          type="checkbox"
        />
        <span>核准時使用 quotaOverride 特批超額送測</span>
      </label>

      <button
        type="button"
        onClick={onReload}
        style={{ ...buttonStyle("blue"), width: "100%", marginTop: 12 }}
      >
        重新整理待簽核清單
      </button>
    </Panel>
  );
}
