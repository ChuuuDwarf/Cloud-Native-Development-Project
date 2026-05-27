export const EXPERIMENTS_KEY = ["experiments"] as const;

export const TABLE_HEADERS = [
  "WIP 編號",
  "委託單",
  "樣品 / 項目",
  "機台",
  "操作人",
  "狀態",
  "進度",
  "操作",
] as const;

/** KPI 卡片設定；``key`` 對應 ``useExecutionPage`` 回傳的 kpi 計數。 */
export const KPI_CARDS = [
  { key: "checkin", label: "待上機", color: "var(--yellow)", icon: "⏱️" },
  { key: "running", label: "執行中", color: "var(--cyan)", icon: "🔬" },
  { key: "out", label: "已下機", color: "var(--orange)", icon: "📤" },
  { key: "confirm", label: "待確認", color: "var(--purple)", icon: "🔍" },
  { key: "done", label: "已完成", color: "var(--green)", icon: "✅" },
] as const;
