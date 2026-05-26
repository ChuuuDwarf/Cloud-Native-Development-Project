"use client";
import Chip from "@/components/ui/Chip";
import Btn from "@/components/ui/Btn";
import { experimentsApi } from "@/services/experiments-api";
import { chipOf, type Wip } from "@/types/lab";
import { TABLE_HEADERS } from "../constants";
import { th, td, tdMono, linkBtn } from "../styles";
import type { ModalKind, RunFn } from "../types";

type OpenFn = (kind: ModalKind, w: Wip) => void;

type ActionProps = {
  w: Wip;
  canOperate: boolean;
  isChief: boolean;
  offline: boolean;
  open: OpenFn;
  run: RunFn;
  flashError: (text: string) => void;
};

function RowActions({ w, canOperate, isChief, offline, open, run, flashError }: ActionProps) {
  const disabled = offline;

  function promptProgress(wip: Wip) {
    const v = window.prompt(`更新 ${wip.wipId} 進度（0-100）`, String(wip.progress));
    if (v === null) return;
    const n = Number(v);
    if (Number.isNaN(n) || n < 0 || n > 100) {
      flashError("進度需為 0-100 的數字");
      return;
    }
    run(() => experimentsApi.updateProgress(wip.wipId, n), "進度已更新");
  }

  const abortPending = w.abort?.status === "待主管判定";
  if (abortPending) {
    return isChief ? (
      <Btn small variant="danger" disabled={disabled} onClick={() => open("review", w)}>
        審核中止
      </Btn>
    ) : (
      <span style={{ fontSize: 10, color: "var(--text3)" }}>待主管判定</span>
    );
  }
  if (!canOperate) {
    return <span style={{ fontSize: 10, color: "var(--text3)" }}>廠區使用者無操作權限</span>;
  }
  switch (w.status) {
    case "待上機":
      return (
        <Btn small variant="primary" disabled={disabled} onClick={() => open("checkin", w)}>
          上機
        </Btn>
      );
    case "執行中":
      return (
        <>
          <Btn small disabled={disabled} onClick={() => promptProgress(w)}>
            更新進度
          </Btn>
          <Btn
            small
            disabled={disabled}
            onClick={() =>
              run(
                () => experimentsApi.checkOut(w.wipId, { operator: w.operator ?? "實驗室人員" }),
                "下機登記完成"
              )
            }
          >
            下機
          </Btn>
          <Btn small variant="primary" disabled={disabled} onClick={() => open("result", w)}>
            上傳結果
          </Btn>
          <Btn small variant="danger" disabled={disabled} onClick={() => open("abort", w)}>
            中止申請
          </Btn>
        </>
      );
    case "已下機":
      return (
        <>
          <Btn small variant="primary" disabled={disabled} onClick={() => open("result", w)}>
            上傳結果
          </Btn>
          <Btn small variant="danger" disabled={disabled} onClick={() => open("abort", w)}>
            中止申請
          </Btn>
        </>
      );
    case "待確認":
      return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          {!w.dataVerified && (
            <>
              <span style={{ fontSize: 10, color: "var(--orange)" }}>⚠️ 數據尚未驗證</span>
              <Btn small disabled={disabled} onClick={() => open("verify", w)}>
                驗證數據
              </Btn>
            </>
          )}
          <Btn
            small
            variant="primary"
            disabled={disabled || !w.dataVerified}
            onClick={() =>
              run(() => experimentsApi.confirm(w.wipId, { operator: "實驗室人員" }), "結果已確認")
            }
          >
            確認結果
          </Btn>
        </span>
      );
    default:
      return <span style={{ fontSize: 10, color: "var(--text3)" }}>—</span>;
  }
}

export default function ExecutionTable({
  wips,
  canOperate,
  isChief,
  offline,
  open,
  run,
  flashError,
}: {
  wips: Wip[];
  canOperate: boolean;
  isChief: boolean;
  offline: boolean;
  open: OpenFn;
  run: RunFn;
  flashError: (text: string) => void;
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
          {wips.map((w) => (
            <tr key={w.wipId} style={{ borderBottom: "1px solid rgba(56,139,253,0.05)" }}>
              <td style={tdMono}>
                <button onClick={() => open("detail", w)} style={linkBtn}>
                  {w.wipId}
                </button>
              </td>
              <td style={tdMono}>{w.orderId}</td>
              <td style={td}>
                {w.sample}
                <div style={{ fontSize: 10, color: "var(--text3)" }}>{w.experimentItem}</div>
              </td>
              <td style={td}>{w.machineId ?? "—"}</td>
              <td style={td}>{w.operator ?? "—"}</td>
              <td style={td}>
                <Chip type={chipOf(w.status)} label={w.status} />
                {w.abort?.status === "待主管判定" && (
                  <div style={{ fontSize: 10, color: "var(--orange)", marginTop: 3 }}>
                    ⚠️ 中止待判定
                  </div>
                )}
              </td>
              <td style={td}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ background: "var(--s3)", borderRadius: 3, height: 5, width: 70 }}>
                    <div
                      style={{
                        width: `${w.progress}%`,
                        height: "100%",
                        borderRadius: 3,
                        background:
                          w.status === "已完成"
                            ? "var(--green)"
                            : "linear-gradient(90deg,var(--blue),var(--cyan))",
                      }}
                    />
                  </div>
                  <span style={{ fontSize: 10, fontFamily: "monospace", color: "var(--text3)" }}>
                    {w.progress}%
                  </span>
                </div>
              </td>
              <td style={td}>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <RowActions
                    w={w}
                    canOperate={canOperate}
                    isChief={isChief}
                    offline={offline}
                    open={open}
                    run={run}
                    flashError={flashError}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
