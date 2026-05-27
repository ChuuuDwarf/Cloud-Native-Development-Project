export const REPORTS_KEY = ["reports"] as const;
export const EXPERIMENTS_KEY = ["experiments"] as const;
export const TEMPLATES_KEY = ["report-templates"] as const;

export const TABLE_HEADERS = ["報告編號", "委託單", "標題", "版本", "狀態", "操作"] as const;

// 草稿區：還可編輯/送審。正式報告：已送出之後的階段。
export const DRAFT_STATUSES = ["草稿", "已改版"];
// 已有正式報告的 WIP 不可重複開立（與後端守門一致）。
export const FORMAL_REPORT_STATUSES = ["已確認", "已發布", "已回傳"];

// 實驗項目分組（對應各實驗室），用於新增報告時勾選要產生假數據的項目。
export const EXPERIMENT_ITEMS_BY_LAB: Record<string, string[]> = {
  材料分析實驗室: ["EDX", "FIB", "SEM"],
  電性測試實驗室: ["CV", "IV", "Probe"],
  可靠度實驗室: ["ESD", "HTOL", "TC"],
};
