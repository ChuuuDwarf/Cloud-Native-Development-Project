"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Modal, { Field, inputStyle } from "@/components/ui/Modal";
import Btn from "@/components/ui/Btn";
import { experimentsApi } from "@/services/experiments-api";
import type { Wip } from "@/types/lab";

export type RunFn = (fn: () => Promise<unknown>, okText: string) => Promise<void>;

type MachineLite = {
  machineId: string;
  name: string;
  status: string;
  supportedItems: string[];
};
type RecipeLite = {
  recipeId: string;
  name: string;
  version: string;
  experimentItem: string;
  machineIds: string[];
};

const BLOCKED = ["故障中", "保養中", "停用"];

// wip_histories.action 是自由字串：B 的樣品/WIP 事件寫英文鍵，C/D 寫中文。
// 這裡把 B 的英文事件對齊成中文顯示；已是中文的事件原樣通過。
const HISTORY_ACTION_LABEL: Record<string, string> = {
  created_from_split: "分貨建立",
  send_to_schedule: "送入排程",
  mark_scheduled: "標記已排程",
  mark_dispatched: "標記已派工",
  start: "開始執行",
  pause: "暫停",
  resume: "恢復執行",
  complete: "完成",
  terminate: "終止",
};

export function CheckinModal({
  w,
  machines,
  recipes,
  run,
  onClose,
}: {
  w: Wip;
  machines: MachineLite[];
  recipes: RecipeLite[];
  run: RunFn;
  onClose: () => void;
}) {
  const [operator, setOperator] = useState("");

  // 此 WIP 所屬實驗室的人員/主管（操作人下拉）。
  const operatorsQuery = useQuery({
    queryKey: ["operators", w.wipId],
    queryFn: () => experimentsApi.getOperators(w.wipId),
  });
  const operators = operatorsQuery.data ?? [];

  // 只列支援此實驗項目、且可用的機台。
  const machineOptions = useMemo(
    () =>
      machines.filter(
        (m) => m.supportedItems.includes(w.experimentItem) && !BLOCKED.includes(m.status)
      ),
    [machines, w.experimentItem]
  );

  // 預選派工已指派的機台（w.machineId），否則第一台。
  const [machineId, setMachineId] = useState(
    () =>
      (w.machineId && machineOptions.some((m) => m.machineId === w.machineId)
        ? w.machineId
        : machineOptions[0]?.machineId) ?? ""
  );

  // 對應「此實驗項目 + 選定機台」的 Recipe。
  const recipeOptions = useMemo(
    () =>
      recipes.filter(
        (r) => r.experimentItem === w.experimentItem && r.machineIds.includes(machineId)
      ),
    [recipes, w.experimentItem, machineId]
  );

  const [recipe, setRecipe] = useState(w.recipe ?? "");
  // 機台一變，若目前 Recipe 不適用就改抓建議/第一個。
  const effectiveRecipe =
    recipe && recipeOptions.some((r) => r.recipeId === recipe)
      ? recipe
      : (recipeOptions[0]?.recipeId ?? "");

  const valid = operator.trim() && machineId && effectiveRecipe;
  return (
    <Modal
      open
      title={`上機登記 · ${w.wipId}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            variant="primary"
            disabled={!valid}
            onClick={() =>
              run(
                () =>
                  experimentsApi.checkIn(w.wipId, {
                    operator,
                    machineId,
                    recipe: effectiveRecipe,
                  }),
                "上機登記完成"
              )
            }
          >
            確認上機
          </Btn>
        </>
      }
    >
      <Field label={`實驗項目`}>
        <input style={inputStyle} value={w.experimentItem} disabled />
      </Field>
      <Field label="操作人 *">
        {operators.length > 0 ? (
          <select style={inputStyle} value={operator} onChange={(e) => setOperator(e.target.value)}>
            <option value="">請選擇操作人</option>
            {operators.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}（{p.role}）
              </option>
            ))}
          </select>
        ) : (
          <input
            style={inputStyle}
            value={operator}
            onChange={(e) => setOperator(e.target.value)}
            placeholder={operatorsQuery.isLoading ? "載入此實驗室人員中…" : "必填"}
          />
        )}
      </Field>
      <Field label="機台 *">
        {machineOptions.length === 0 ? (
          <p style={{ fontSize: 11, color: "var(--orange)" }}>
            找不到支援「{w.experimentItem}」的可用機台，請先到「機台管理」設定。
          </p>
        ) : (
          <select
            style={inputStyle}
            value={machineId}
            onChange={(e) => {
              setMachineId(e.target.value);
              setRecipe(""); // 換機台後重抓 Recipe
            }}
          >
            {machineOptions.map((m) => (
              <option key={m.machineId} value={m.machineId}>
                {m.machineId} · {m.name}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field label="RECIPE 版本 *">
        {recipeOptions.length === 0 ? (
          <p style={{ fontSize: 11, color: "var(--orange)" }}>
            此機台無對應「{w.experimentItem}」的 Recipe,請先到「Recipe 管理」建立。
          </p>
        ) : (
          <select
            style={inputStyle}
            value={effectiveRecipe}
            onChange={(e) => setRecipe(e.target.value)}
          >
            {recipeOptions.map((r) => (
              <option key={r.recipeId} value={r.recipeId}>
                {r.recipeId} · {r.name} ({r.version})
              </option>
            ))}
          </select>
        )}
      </Field>
      {!valid && (
        <p style={{ fontSize: 11, color: "var(--orange)" }}>請填操作人,並選擇機台與 Recipe</p>
      )}
    </Modal>
  );
}

export function ResultModal({ w, run, onClose }: { w: Wip; run: RunFn; onClose: () => void }) {
  const [note, setNote] = useState("");
  const [rawDataUrl, setRawDataUrl] = useState("");
  const [verified, setVerified] = useState(false);
  return (
    <Modal
      open
      title={`上傳結果 · ${w.wipId}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            variant="primary"
            disabled={!note.trim()}
            onClick={() =>
              run(
                () =>
                  experimentsApi.uploadResult(w.wipId, {
                    note,
                    rawDataUrl: rawDataUrl || null,
                    dataVerified: verified,
                  }),
                "結果已上傳，進入待結果確認"
              )
            }
          >
            上傳
          </Btn>
        </>
      }
    >
      <Field label="結果備註 *">
        <textarea
          style={{ ...inputStyle, minHeight: 80, resize: "vertical" }}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="必填"
        />
      </Field>
      <Field label="原始數據連結">
        <input
          style={inputStyle}
          value={rawDataUrl}
          onChange={(e) => setRawDataUrl(e.target.value)}
          placeholder="/data/xxx.csv"
        />
      </Field>
      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 12,
          color: "var(--text2)",
        }}
      >
        <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} />
        已驗證數據完整性（未勾選將無法在下一步確認結果）
      </label>
    </Modal>
  );
}

export function AbortModal({ w, run, onClose }: { w: Wip; run: RunFn; onClose: () => void }) {
  const [reason, setReason] = useState("");
  return (
    <Modal
      open
      title={`提出中止申請 · ${w.wipId}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            variant="danger"
            disabled={!reason.trim()}
            onClick={() =>
              run(() => experimentsApi.abortRequest(w.wipId, reason), "已提出中止申請，待主管判定")
            }
          >
            送出申請
          </Btn>
        </>
      }
    >
      <p style={{ fontSize: 12, color: "var(--text3)", marginBottom: 12 }}>
        實驗室人員不可直接終止實驗，送出後須由主管審核決定。
      </p>
      <Field label="中止原因 *">
        <textarea
          style={{ ...inputStyle, minHeight: 80, resize: "vertical" }}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="必填"
        />
      </Field>
    </Modal>
  );
}

export function ReviewModal({ w, run, onClose }: { w: Wip; run: RunFn; onClose: () => void }) {
  const [note, setNote] = useState("");
  return (
    <Modal
      open
      title={`審核中止申請 · ${w.wipId}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            onClick={() =>
              run(
                () => experimentsApi.abortReview(w.wipId, { approve: false, note }),
                "已駁回，實驗繼續"
              )
            }
          >
            駁回（繼續實驗）
          </Btn>
          <Btn
            variant="danger"
            onClick={() =>
              run(() => experimentsApi.abortReview(w.wipId, { approve: true, note }), "已核准終止")
            }
          >
            核准終止
          </Btn>
        </>
      }
    >
      <div
        style={{
          background: "var(--s2)",
          borderRadius: 8,
          padding: 12,
          marginBottom: 14,
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
          申請原因（{w.abort?.by}）
        </div>
        {w.abort?.reason}
      </div>
      <Field label="處理結果說明">
        <textarea
          style={{ ...inputStyle, minHeight: 60, resize: "vertical" }}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </Field>
    </Modal>
  );
}

// 量測數據顯示（{實驗項目: {欄位: 值}}）—— 驗證 modal 與機台履歷共用。
function ExperimentDataBlock({ data }: { data?: Record<string, Record<string, string>> }) {
  const entries = Object.entries(data ?? {});
  if (entries.length === 0) {
    return <div style={{ fontSize: 12, color: "var(--text3)" }}>（此實驗無保存的量測數據）</div>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {entries.map(([item, fields]) => (
        <div key={item} style={{ background: "var(--s2)", borderRadius: 8, padding: 12 }}>
          <div
            style={{
              fontSize: 11,
              fontFamily: "monospace",
              color: "var(--cyan)",
              marginBottom: 8,
            }}
          >
            {item}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "6px 16px",
              fontSize: 12.5,
            }}
          >
            {Object.entries(fields).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ color: "var(--text3)" }}>{k}</span>
                <span style={{ fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function VerifyModal({ w, run, onClose }: { w: Wip; run: RunFn; onClose: () => void }) {
  return (
    <Modal
      open
      title={`驗證實驗數據 · ${w.wipId}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn
            variant="primary"
            onClick={() =>
              run(() => experimentsApi.verify(w.wipId, { operator: "實驗室人員" }), "數據已驗證")
            }
          >
            確認數據無誤，完成驗證
          </Btn>
        </>
      }
    >
      <p style={{ fontSize: 12, color: "var(--text3)", marginBottom: 12 }}>
        請確認以下機台收集的量測數據無誤；通過驗證後才能確認結果。
      </p>
      <div
        style={{
          fontSize: 11,
          fontFamily: "monospace",
          color: "var(--text3)",
          marginBottom: 8,
        }}
      >
        量測數據{w.rawDataUrl ? ` · 原始檔：${w.rawDataUrl}` : ""}
      </div>
      <ExperimentDataBlock data={w.experimentData} />
    </Modal>
  );
}

export function DetailModal({ w, onClose }: { w: Wip; onClose: () => void }) {
  return (
    <Modal open title={`機台履歷 · ${w.wipId}`} onClose={onClose}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          marginBottom: 16,
          fontSize: 12.5,
        }}
      >
        <Info label="委託單" v={w.orderId} />
        <Info label="樣品" v={w.sample} />
        <Info label="機台" v={w.machineId ?? "—"} />
        <Info label="Recipe" v={w.recipe ?? "—"} />
        <Info label="上機時間" v={w.checkInAt ?? "—"} />
        <Info label="下機時間" v={w.checkOutAt ?? "—"} />
        <Info label="數據驗證" v={w.dataVerified ? "已驗證" : "未驗證"} />
        <Info label="原始數據" v={w.rawDataUrl ?? "—"} />
      </div>
      {w.resultNote && (
        <div
          style={{
            background: "var(--s2)",
            borderRadius: 8,
            padding: 12,
            marginBottom: 16,
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
            結果備註
          </div>
          {w.resultNote}
        </div>
      )}
      {Object.keys(w.experimentData ?? {}).length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 11,
              fontFamily: "monospace",
              color: "var(--text3)",
              marginBottom: 8,
            }}
          >
            量測數據
          </div>
          <ExperimentDataBlock data={w.experimentData} />
        </div>
      )}
      <div
        style={{
          fontSize: 11,
          fontFamily: "monospace",
          color: "var(--text3)",
          letterSpacing: 1,
          marginBottom: 10,
        }}
      >
        上下貨履歷（不可刪除）
      </div>
      {w.history.length === 0 ? (
        <div style={{ fontSize: 12, color: "var(--text3)" }}>尚無履歷紀錄</div>
      ) : (
        w.history.map((h, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              gap: 12,
              paddingBottom: 14,
              position: "relative",
            }}
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
                <strong>{HISTORY_ACTION_LABEL[h.action] ?? h.action}</strong>
                {h.note ? ` · ${h.note}` : ""}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text3)",
                  fontFamily: "monospace",
                  marginTop: 2,
                }}
              >
                {h.time} · {h.by}
              </div>
            </div>
          </div>
        ))
      )}
    </Modal>
  );
}

function Info({ label, v }: { label: string; v: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "monospace" }}>{label}</div>
      <div style={{ marginTop: 2 }}>{v}</div>
    </div>
  );
}
