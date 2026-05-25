"use client";
import { useState } from "react";
import Chip from "@/components/ui/Chip";
import Panel from "@/components/ui/Panel";
import Btn from "@/components/ui/Btn";
import DataState, { OfflineBanner } from "@/components/ui/DataState";
import Modal from "@/components/ui/Modal";
import RoleSwitcher from "@/components/ui/RoleSwitcher";
import { useQueryClient } from "@tanstack/react-query";
import { useResourceQuery } from "@/hooks/useResourceQuery";
import { errorMessage } from "@/lib/errorMessage";
import { closuresApi } from "@/services/closures-api";
import { MOCK_CLOSURES } from "@/mocks/lab";
import { chipOf, type ClosureCheck, type Role } from "@/types/lab";

const CLOSURES_KEY = ["closures"] as const;

export default function ClosurePage() {
  const queryClient = useQueryClient();
  const {
    data: rows,
    loading,
    offline,
    reload,
  } = useResourceQuery<ClosureCheck[]>(
    CLOSURES_KEY,
    closuresApi.list,
    MOCK_CLOSURES,
  );
  const [role, setRole] = useState<Role>("實驗室人員");
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [detail, setDetail] = useState<ClosureCheck | null>(null);
  const isStaff = role === "實驗室人員";

  // run() preserves the old success/error banner UX, but writes now go through
  // the service (cookie auth, no X-Role) and invalidate the React Query cache.
  async function run(fn: () => Promise<unknown>, okText: string) {
    try {
      await fn();
      setMsg({ text: okText, ok: true });
      await queryClient.invalidateQueries({ queryKey: CLOSURES_KEY });
      reload();
    } catch (e) {
      setMsg({ text: errorMessage(e), ok: false });
    }
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>
            結單管理
          </h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--text3)",
              marginTop: 4,
              fontFamily: "monospace",
            }}
          >
            CLOSURE · 結單條件檢核 → 轉待取件
          </p>
        </div>
        <RoleSwitcher role={role} onChange={setRole} />
      </div>

      {offline && <OfflineBanner />}
      {msg && (
        <div
          style={{
            marginBottom: 16,
            padding: "8px 14px",
            borderRadius: 8,
            fontSize: 12.5,
            background: msg.ok ? "rgba(63,185,80,0.1)" : "rgba(255,68,68,0.1)",
            border: `1px solid ${msg.ok ? "rgba(63,185,80,0.3)" : "rgba(255,68,68,0.3)"}`,
            color: msg.ok ? "var(--green)" : "var(--red)",
          }}
        >
          {msg.ok ? "✅ " : "⚠️ "}
          {msg.text}
        </div>
      )}

      <Panel title="委託單結單狀態" tag={`${rows.length} 筆`}>
        <DataState loading={loading} empty={rows.length === 0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--s2)" }}>
                  {["委託單", "目前狀態", "結單條件", "可否結單", "操作"].map(
                    (h) => (
                      <th key={h} style={th}>
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => {
                  const met = c.conditions.filter((x) => x.ok).length;
                  return (
                    <tr
                      key={c.orderId}
                      style={{
                        borderBottom: "1px solid rgba(56,139,253,0.05)",
                      }}
                    >
                      <td style={tdMono}>
                        <button onClick={() => setDetail(c)} style={linkBtn}>
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
                            color:
                              met === c.conditions.length
                                ? "var(--green)"
                                : "var(--text3)",
                          }}
                        >
                          {met}/{c.conditions.length} 達成
                        </span>
                      </td>
                      <td style={td}>
                        {c.canClose ? (
                          <span style={{ color: "var(--green)", fontSize: 11 }}>
                            ✅ 可結單
                          </span>
                        ) : (
                          <span style={{ color: "var(--text3)", fontSize: 11 }}>
                            條件未滿足
                          </span>
                        )}
                      </td>
                      <td style={td}>
                        {c.status === "已結案" ? (
                          <span style={{ fontSize: 10, color: "var(--text3)" }}>
                            已結案
                          </span>
                        ) : c.status === "待取件" ? (
                          <span style={{ fontSize: 10, color: "var(--blue)" }}>
                            請至倉儲取件結案
                          </span>
                        ) : isStaff ? (
                          <Btn
                            small
                            variant="primary"
                            disabled={offline || !c.canClose}
                            title={c.canClose ? "" : "尚未滿足結單條件"}
                            onClick={() =>
                              run(
                                () => closuresApi.toPickup(c.orderId),
                                "已轉待取件",
                              )
                            }
                          >
                            轉待取件
                          </Btn>
                        ) : (
                          <span style={{ fontSize: 10, color: "var(--text3)" }}>
                            僅實驗室人員可操作
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </DataState>
      </Panel>

      {detail && (
        <Modal
          open
          title={`結單條件 · ${detail.orderId}`}
          onClose={() => setDetail(null)}
        >
          <p style={{ fontSize: 12, color: "var(--text3)", marginBottom: 14 }}>
            需全部滿足才可轉待取件（依 result_manage.md）。
          </p>
          {detail.conditions.map((cond, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 0",
                borderBottom: "1px solid var(--border2)",
                fontSize: 13,
              }}
            >
              <span style={{ fontSize: 16 }}>{cond.ok ? "✅" : "⬜"}</span>
              <span style={{ color: cond.ok ? "var(--text)" : "var(--text3)" }}>
                {cond.name}
              </span>
            </div>
          ))}
        </Modal>
      )}
    </div>
  );
}

const th = {
  fontSize: 10,
  letterSpacing: 1.5,
  color: "var(--text3)",
  padding: "10px 16px",
  textAlign: "left" as const,
  fontFamily: "monospace",
  borderBottom: "1px solid var(--border2)",
  whiteSpace: "nowrap" as const,
};
const td = {
  padding: "11px 16px",
  fontSize: 12.5,
  verticalAlign: "middle" as const,
};
const tdMono = {
  ...td,
  fontFamily: "monospace",
  fontSize: 11.5,
  color: "var(--text2)",
};
const linkBtn = {
  background: "none",
  border: "none",
  color: "var(--blue)",
  cursor: "pointer",
  fontFamily: "monospace",
  fontSize: 11.5,
  padding: 0,
  textDecoration: "underline",
};
