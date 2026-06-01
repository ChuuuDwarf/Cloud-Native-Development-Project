"use client";
import Chip from "@/components/ui/Chip";
import Btn from "@/components/ui/Btn";
import { closuresApi } from "@/services/closures-api";
import { chipOf } from "@/types/lab";
import type { ClosureCheck } from "../types";
import { TABLE_HEADERS } from "../constants";
import { th, td, tdMono, linkBtn } from "../styles";

export type RunFn = (fn: () => Promise<unknown>, okText: string) => Promise<void>;

const noPerm = <span style={{ fontSize: 10, color: "var(--text3)" }}>廠區使用者無操作權限</span>;

function ClosureAction({
  c,
  canOperate,
  offline,
  run,
}: {
  c: ClosureCheck;
  canOperate: boolean;
  offline: boolean;
  run: RunFn;
}) {
  if (c.status === "已結案") {
    return <span style={{ fontSize: 10, color: "var(--text3)" }}>已結案</span>;
  }
  // Cross-lab closure: THIS lab pressed to_pickup but the order is still
  // waiting for other labs to do the same. The button is hidden — the
  // active state for this caller has moved to "waiting".
  if (c.labClosed && c.status !== "待送件") {
    return (
      <span style={{ fontSize: 10, color: "var(--orange)" }}>本實驗室已結單，等待其他實驗室</span>
    );
  }
  if (c.status === "待送件") {
    if (!canOperate) return noPerm;
    // 條件閘門：6 條件全滿足(含樣品已交付)才可送件結案；否則停用。
    return (
      <Btn
        small
        variant="primary"
        disabled={offline || !c.canClose}
        title={c.canClose ? "" : "尚未滿足結單條件（請先至樣品交付頁通知使用者取件）"}
        onClick={() =>
          run(() => closuresApi.close(c.orderId, { operator: "實驗室人員" }), "已送件結案")
        }
      >
        送件結案
      </Btn>
    );
  }
  if (!canOperate) return noPerm;
  return (
    <Btn
      small
      variant="primary"
      disabled={offline || !c.canClose}
      title={c.canClose ? "" : "尚未滿足結單條件"}
      onClick={() => run(() => closuresApi.toPickup(c.orderId), "已轉待送件")}
    >
      轉待送件
    </Btn>
  );
}

export default function ClosureTable({
  rows,
  canOperate,
  offline,
  onDetail,
  run,
}: {
  rows: ClosureCheck[];
  canOperate: boolean;
  offline: boolean;
  onDetail: (c: ClosureCheck) => void;
  run: RunFn;
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--s2)" }}>
            {TABLE_HEADERS.map((h) => (
              <th key={h} style={th}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => {
            const met = c.conditions.filter((x) => x.ok).length;
            return (
              <tr key={c.orderId} style={{ borderBottom: "1px solid rgba(56,139,253,0.05)" }}>
                <td style={tdMono}>
                  <button onClick={() => onDetail(c)} style={linkBtn}>
                    {c.orderId}
                  </button>
                </td>
                <td style={td}>
                  <Chip type={chipOf(c.status)} label={c.status} />
                </td>
                <td style={td}>
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: 11,
                      color: met === c.conditions.length ? "var(--green)" : "var(--text3)",
                    }}
                  >
                    {met}/{c.conditions.length} 達成
                  </span>
                </td>
                <td style={td}>
                  {c.canClose ? (
                    <span style={{ color: "var(--green)", fontSize: 11 }}>✅ 可結單</span>
                  ) : (
                    <span style={{ color: "var(--text3)", fontSize: 11 }}>條件未滿足</span>
                  )}
                </td>
                <td style={td}>
                  <ClosureAction c={c} canOperate={canOperate} offline={offline} run={run} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
