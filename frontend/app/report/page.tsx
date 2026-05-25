"use client";
import { useState } from "react";
import Chip from "@/components/ui/Chip";
import Panel from "@/components/ui/Panel";
import Btn from "@/components/ui/Btn";
import DataState, { OfflineBanner } from "@/components/ui/DataState";
import Modal, { Field, inputStyle } from "@/components/ui/Modal";
import RoleSwitcher from "@/components/ui/RoleSwitcher";
import { useQueryClient } from "@tanstack/react-query";
import { useResourceQuery } from "@/hooks/useResourceQuery";
import { errorMessage } from "@/lib/errorMessage";
import { reportsApi } from "@/services/reports-api";
import { experimentsApi } from "@/services/experiments-api";
import { MOCK_REPORTS, MOCK_WIPS } from "@/mocks/lab";
import { chipOf, type Report, type Role, type Wip } from "@/types/lab";

const REPORTS_KEY = ["reports"] as const;
const EXPERIMENTS_KEY = ["experiments"] as const;

export default function ReportPage() {
  const queryClient = useQueryClient();
  const {
    data: reports,
    loading,
    offline,
    reload,
  } = useResourceQuery<Report[]>(REPORTS_KEY, reportsApi.list, MOCK_REPORTS);
  const { data: wips } = useResourceQuery<Wip[]>(
    EXPERIMENTS_KEY,
    experimentsApi.list,
    MOCK_WIPS,
  );
  const [role, setRole] = useState<Role>("實驗室人員");
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [detail, setDetail] = useState<Report | null>(null);
  const [editing, setEditing] = useState<Report | null>(null);
  const [creating, setCreating] = useState(false);

  const isStaff = role === "實驗室人員";
  const isChief = role === "實驗室主管";
  // 比照後端角色繼承（deps.ROLE_INCLUDES）：主管含人員權限，故可建立/編輯/送審報告
  const canStaff = isStaff || isChief;
  const creatable = wips.filter(
    (w) => w.status === "待確認" || w.status === "已完成",
  );

  // run() keeps the old success/error banner UX. Writes go through the report
  // service (cookie auth, no X-Role) and invalidate the React Query cache.
  async function run(fn: () => Promise<unknown>, okText: string) {
    try {
      await fn();
      setMsg({ text: okText, ok: true });
      setEditing(null);
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
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
            實驗報告管理
          </h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--text3)",
              marginTop: 4,
              fontFamily: "monospace",
            }}
          >
            REPORT · 草稿 → 待審核 → 已確認 → 已發布 → 已回傳
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <RoleSwitcher role={role} onChange={setRole} />
          <Btn
            variant="primary"
            disabled={offline || !canStaff}
            onClick={() => {
              setCreating(true);
              setMsg(null);
            }}
          >
            ＋ 新增報告
          </Btn>
        </div>
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

      <Panel title="報告清單" tag={`${reports.length} 筆`}>
        <DataState
          loading={loading}
          empty={reports.length === 0}
          emptyText="尚無報告，可從已完成的實驗建立"
        >
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--s2)" }}>
                  {["報告編號", "委託單", "標題", "版本", "狀態", "操作"].map(
                    (h) => (
                      <th key={h} style={th}>
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr
                    key={r.reportId}
                    style={{ borderBottom: "1px solid rgba(56,139,253,0.05)" }}
                  >
                    <td style={tdMono}>
                      <button onClick={() => setDetail(r)} style={linkBtn}>
                        {r.reportId}
                      </button>
                    </td>
                    <td style={tdMono}>{r.orderId}</td>
                    <td style={td}>{r.title}</td>
                    <td style={tdMono}>v{r.versions.length}</td>
                    <td style={td}>
                      <Chip type={chipOf(r.status)} label={r.status} />
                    </td>
                    <td style={td}>
                      <div
                        style={{ display: "flex", gap: 6, flexWrap: "wrap" }}
                      >
                        {actions(r)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataState>
      </Panel>

      {detail && <DetailModal r={detail} onClose={() => setDetail(null)} />}
      {editing && (
        <EditModal r={editing} run={run} onClose={() => setEditing(null)} />
      )}
      {creating && (
        <CreateModal
          wips={creatable}
          run={run}
          onClose={() => setCreating(false)}
        />
      )}
    </div>
  );

  function actions(r: Report) {
    const d = offline;
    if ((r.status === "草稿" || r.status === "已改版") && canStaff) {
      return (
        <>
          <Btn
            small
            disabled={d}
            onClick={() => {
              setEditing(r);
              setMsg(null);
            }}
          >
            編輯
          </Btn>
          <Btn
            small
            variant="primary"
            disabled={d}
            onClick={() =>
              run(() => reportsApi.submit(r.reportId), "已提交審核")
            }
          >
            送審
          </Btn>
        </>
      );
    }
    if (r.status === "待審核" && isChief) {
      return (
        <>
          <Btn
            small
            disabled={d}
            onClick={() =>
              run(
                () => reportsApi.review(r.reportId, { approve: false }),
                "報告已退回",
              )
            }
          >
            退回
          </Btn>
          <Btn
            small
            variant="primary"
            disabled={d}
            onClick={() =>
              run(
                () => reportsApi.review(r.reportId, { approve: true }),
                "報告已確認",
              )
            }
          >
            確認
          </Btn>
        </>
      );
    }
    if (r.status === "已確認" && canStaff) {
      return (
        <Btn
          small
          variant="primary"
          disabled={d}
          onClick={() =>
            run(() => reportsApi.publish(r.reportId), "報告已發布並回傳")
          }
        >
          發布回傳
        </Btn>
      );
    }
    if (r.status === "已發布" || r.status === "已回傳") {
      return (
        <Btn small onClick={() => setDetail(r)}>
          查閱 / 下載
        </Btn>
      );
    }
    return <span style={{ fontSize: 10, color: "var(--text3)" }}>—</span>;
  }
}

function CreateModal({
  wips,
  run,
  onClose,
}: {
  wips: Wip[];
  run: (fn: () => Promise<unknown>, ok: string) => Promise<void>;
  onClose: () => void;
}) {
  const [wipId, setWipId] = useState(wips[0]?.wipId ?? "");
  return (
    <Modal
      open
      title="從實驗結果建立報告草稿"
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            variant="primary"
            disabled={!wipId}
            onClick={() =>
              run(() => reportsApi.create(wipId), "已建立報告草稿")
            }
          >
            建立草稿
          </Btn>
        </>
      }
    >
      {wips.length === 0 ? (
        <p style={{ fontSize: 12.5, color: "var(--text3)" }}>
          目前沒有「待確認 / 已完成」的實驗可建立報告。
        </p>
      ) : (
        <Field label="來源 WIP（待確認 / 已完成）">
          <select
            style={inputStyle}
            value={wipId}
            onChange={(e) => setWipId(e.target.value)}
          >
            {wips.map((w) => (
              <option key={w.wipId} value={w.wipId}>
                {w.wipId} · {w.experimentItem}（{w.status}）
              </option>
            ))}
          </select>
        </Field>
      )}
    </Modal>
  );
}

function EditModal({
  r,
  run,
  onClose,
}: {
  r: Report;
  run: (fn: () => Promise<unknown>, ok: string) => Promise<void>;
  onClose: () => void;
}) {
  const [summary, setSummary] = useState(r.summary);
  const [conclusion, setConclusion] = useState(r.conclusion);
  const [attachmentName, setAttachmentName] = useState("");
  return (
    <Modal
      open
      title={`編輯報告 · ${r.reportId}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            variant="primary"
            onClick={() =>
              run(
                () =>
                  reportsApi.edit(r.reportId, {
                    summary,
                    conclusion,
                    attachmentName: attachmentName || null,
                  }),
                "報告已更新",
              )
            }
          >
            儲存
          </Btn>
        </>
      }
    >
      <Field label="摘要">
        <textarea
          style={{ ...inputStyle, minHeight: 70, resize: "vertical" }}
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
      </Field>
      <Field label="結論">
        <textarea
          style={{ ...inputStyle, minHeight: 70, resize: "vertical" }}
          value={conclusion}
          onChange={(e) => setConclusion(e.target.value)}
        />
      </Field>
      <Field label="新增附件檔名">
        <input
          style={inputStyle}
          value={attachmentName}
          onChange={(e) => setAttachmentName(e.target.value)}
          placeholder="report.pdf（選填）"
        />
      </Field>
    </Modal>
  );
}

function DetailModal({ r, onClose }: { r: Report; onClose: () => void }) {
  return (
    <Modal open title={`${r.reportId} · ${r.title}`} onClose={onClose}>
      <div
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 14,
          alignItems: "center",
        }}
      >
        <Chip type={chipOf(r.status)} label={r.status} />
        <span
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          {r.orderId} · 建立者 {r.createdBy}
        </span>
      </div>
      <Block label="摘要" v={r.summary} />
      <Block label="結論" v={r.conclusion} />
      {r.attachments.length > 0 && (
        <Block label="附件" v={r.attachments.map((a) => a.name).join("、")} />
      )}
      <div
        style={{
          fontSize: 11,
          fontFamily: "monospace",
          color: "var(--text3)",
          letterSpacing: 1,
          margin: "16px 0 10px",
        }}
      >
        版本紀錄
      </div>
      {r.versions.map((v) => (
        <div
          key={v.version}
          style={{ display: "flex", gap: 12, paddingBottom: 12 }}
        >
          <div
            style={{
              width: 13,
              height: 13,
              borderRadius: "50%",
              border: "2px solid var(--blue)",
              background: "rgba(56,139,253,0.15)",
              flexShrink: 0,
              marginTop: 2,
            }}
          />
          <div>
            <div style={{ fontSize: 12.5 }}>
              <strong>v{v.version}</strong> · {v.status}
              {v.note ? ` · ${v.note}` : ""}
            </div>
            <div
              style={{
                fontSize: 10,
                color: "var(--text3)",
                fontFamily: "monospace",
                marginTop: 2,
              }}
            >
              {v.at} · {v.by}
            </div>
          </div>
        </div>
      ))}
    </Modal>
  );
}

function Block({ label, v }: { label: string; v: string }) {
  return (
    <div
      style={{
        background: "var(--s2)",
        borderRadius: 8,
        padding: 12,
        marginBottom: 10,
        fontSize: 12.5,
      }}
    >
      <div
        style={{
          color: "var(--text3)",
          fontSize: 10,
          fontFamily: "monospace",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      {v || "—"}
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
