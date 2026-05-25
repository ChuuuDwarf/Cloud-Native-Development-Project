"use client";

import { useState } from "react";
import Modal, { Field, inputStyle } from "@/components/ui/Modal";
import Btn from "@/components/ui/Btn";
import { experimentsApi } from "@/services/experiments-api";
import type { Wip } from "@/types/lab";

export type RunFn = (
  fn: () => Promise<unknown>,
  okText: string,
) => Promise<void>;

export function CheckinModal({
  w,
  run,
  onClose,
}: {
  w: Wip;
  run: RunFn;
  onClose: () => void;
}) {
  const [operator, setOperator] = useState("");
  const [machineId, setMachineId] = useState(w.machineId ?? "");
  const [recipe, setRecipe] = useState(w.recipe ?? "");
  const valid = operator.trim() && machineId.trim() && recipe.trim();
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
                    recipe,
                  }),
                "上機登記完成",
              )
            }
          >
            確認上機
          </Btn>
        </>
      }
    >
      <Field label="操作人 *">
        <input
          style={inputStyle}
          value={operator}
          onChange={(e) => setOperator(e.target.value)}
          placeholder="必填"
        />
      </Field>
      <Field label="機台編號 *">
        <input
          style={inputStyle}
          value={machineId}
          onChange={(e) => setMachineId(e.target.value)}
        />
      </Field>
      <Field label="RECIPE 版本 *">
        <input
          style={inputStyle}
          value={recipe}
          onChange={(e) => setRecipe(e.target.value)}
        />
      </Field>
      {!valid && (
        <p style={{ fontSize: 11, color: "var(--orange)" }}>
          操作人、機台、Recipe 為必填
        </p>
      )}
    </Modal>
  );
}

export function ResultModal({
  w,
  run,
  onClose,
}: {
  w: Wip;
  run: RunFn;
  onClose: () => void;
}) {
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
                "結果已上傳，進入待結果確認",
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
        <input
          type="checkbox"
          checked={verified}
          onChange={(e) => setVerified(e.target.checked)}
        />
        已驗證數據完整性（未勾選將無法在下一步確認結果）
      </label>
    </Modal>
  );
}

export function AbortModal({
  w,
  run,
  onClose,
}: {
  w: Wip;
  run: RunFn;
  onClose: () => void;
}) {
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
              run(
                () => experimentsApi.abortRequest(w.wipId, reason),
                "已提出中止申請，待主管判定",
              )
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

export function ReviewModal({
  w,
  run,
  onClose,
}: {
  w: Wip;
  run: RunFn;
  onClose: () => void;
}) {
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
                () =>
                  experimentsApi.abortReview(w.wipId, { approve: false, note }),
                "已駁回，實驗繼續",
              )
            }
          >
            駁回（繼續實驗）
          </Btn>
          <Btn
            variant="danger"
            onClick={() =>
              run(
                () =>
                  experimentsApi.abortReview(w.wipId, { approve: true, note }),
                "已核准終止",
              )
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
                <strong>{h.action}</strong>
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
      <div
        style={{ fontSize: 10, color: "var(--text3)", fontFamily: "monospace" }}
      >
        {label}
      </div>
      <div style={{ marginTop: 2 }}>{v}</div>
    </div>
  );
}
