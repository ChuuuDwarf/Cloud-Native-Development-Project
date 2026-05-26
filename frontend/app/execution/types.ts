export type { Wip } from "@/types/lab";
export type { RunFn } from "./components/modals";

export type ModalKind = "checkin" | "result" | "abort" | "review" | "verify" | "detail" | null;

/** 操作成功/失敗提示橫幅。 */
export type Banner = { text: string; ok: boolean };
