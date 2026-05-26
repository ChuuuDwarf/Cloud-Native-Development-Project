"use client";
import { useState } from "react";
import Btn from "@/components/ui/Btn";
import Modal, { Field, inputStyle } from "@/components/ui/Modal";
import { reportsApi } from "@/services/reports-api";
import { EXPERIMENT_ITEMS_BY_LAB } from "../constants";
import type { ReportTemplate, RunFn, Wip } from "../types";

export default function CreateModal({
  wips,
  templates,
  run,
  onClose,
}: {
  wips: Wip[];
  templates: ReportTemplate[];
  run: RunFn;
  onClose: () => void;
}) {
  const [wipId, setWipId] = useState(wips[0]?.wipId ?? "");
  const selectedWip = wips.find((w) => w.wipId === wipId);
  const [templateId, setTemplateId] = useState<number | "">("");
  const [summary, setSummary] = useState("");
  const [conclusion, setConclusion] = useState("");
  // 預設勾選此 WIP 的實驗項目（生對應假數據）。
  const [items, setItems] = useState<string[]>(() =>
    selectedWip?.experimentItem ? [selectedWip.experimentItem] : []
  );

  function toggleItem(item: string) {
    setItems((cur) => (cur.includes(item) ? cur.filter((i) => i !== item) : [...cur, item]));
  }

  function submit(doSubmit: boolean) {
    run(
      () =>
        reportsApi.create(wipId, {
          summary: summary || null,
          conclusion: conclusion || null,
          experimentItems: items.length > 0 ? items : undefined,
          templateId: templateId === "" ? null : templateId,
          submit: doSubmit,
        }),
      doSubmit ? "已建立並送審" : "已建立報告草稿"
    );
  }

  return (
    <Modal
      open
      title="新增報告（填內容 → 建立 / 送審）"
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>取消</Btn>
          <Btn disabled={!wipId} onClick={() => submit(false)}>
            建立草稿
          </Btn>
          <Btn variant="primary" disabled={!wipId} onClick={() => submit(true)}>
            建立並送審
          </Btn>
        </>
      }
    >
      {wips.length === 0 ? (
        <p style={{ fontSize: 12.5, color: "var(--text3)" }}>
          目前沒有「待確認 / 已完成」的實驗可建立報告。
        </p>
      ) : (
        <>
          <Field label="來源 WIP（待確認 / 已完成）">
            <select
              style={inputStyle}
              value={wipId}
              onChange={(e) => {
                setWipId(e.target.value);
                const w = wips.find((x) => x.wipId === e.target.value);
                setItems(w?.experimentItem ? [w.experimentItem] : []);
              }}
            >
              {wips.map((w) => (
                <option key={w.wipId} value={w.wipId}>
                  {w.wipId} · {w.experimentItem}（{w.status}）
                </option>
              ))}
            </select>
          </Field>

          <Field label="套用範本（選填，帶入摘要/結論）">
            <select
              style={inputStyle}
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">不套用範本</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                  {t.orderId ? `（${t.orderId}）` : ""}
                </option>
              ))}
            </select>
          </Field>

          <Field label="實驗項目（勾選要產生數據的項目）">
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {Object.entries(EXPERIMENT_ITEMS_BY_LAB).map(([lab, labItems]) => (
                <div key={lab}>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "var(--text2)",
                      marginBottom: 4,
                    }}
                  >
                    {lab}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                    {labItems.map((item) => (
                      <label
                        key={item}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          fontSize: 12.5,
                          color: "var(--text2)",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={items.includes(item)}
                          onChange={() => toggleItem(item)}
                        />
                        {item}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Field>

          <Field label="摘要（留空自動帶入實驗數值）">
            <textarea
              style={{ ...inputStyle, minHeight: 60, resize: "vertical" }}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="留空 → 自動帶入機台/Recipe/操作人/上下機/數據驗證"
            />
          </Field>
          <Field label="結論（留空用實驗結果備註）">
            <textarea
              style={{ ...inputStyle, minHeight: 60, resize: "vertical" }}
              value={conclusion}
              onChange={(e) => setConclusion(e.target.value)}
            />
          </Field>
        </>
      )}
    </Modal>
  );
}
