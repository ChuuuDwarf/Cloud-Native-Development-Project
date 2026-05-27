export type { Report, ReportTemplate, Wip } from "@/types/lab";

/** 操作成功/失敗提示橫幅。 */
export type Banner = { text: string; ok: boolean };

export type RunFn = (fn: () => Promise<unknown>, okText: string) => Promise<void>;
