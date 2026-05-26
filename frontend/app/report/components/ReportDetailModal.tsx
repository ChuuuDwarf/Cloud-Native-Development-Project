"use client";
import Btn from "@/components/ui/Btn";
import Modal from "@/components/ui/Modal";
import Chip from "@/components/ui/Chip";
import { chipOf } from "@/types/lab";
import type { Report } from "../types";
import { downloadReport } from "../lib/download";
import { blockStyle, blockLabelStyle } from "../styles";

function Block({ label, v }: { label: string; v: string }) {
  return (
    <div style={blockStyle}>
      <div style={blockLabelStyle}>{label}</div>
      {v || "—"}
    </div>
  );
}

export default function ReportDetailModal({
  r,
  onClose,
  onSaveTemplate,
}: {
  r: Report;
  onClose: () => void;
  onSaveTemplate: (r: Report) => void;
}) {
  const experimentData = r.experimentData ?? {};
  return (
    <Modal
      open
      title={`${r.reportId} · ${r.title}`}
      onClose={onClose}
      footer={
        <>
          <Btn onClick={onClose}>關閉</Btn>
          <Btn onClick={() => onSaveTemplate(r)}>存成範本</Btn>
          <Btn variant="primary" onClick={() => downloadReport(r)}>
            ⬇ 下載報告（.md）
          </Btn>
        </>
      }
    >
      <div style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "center" }}>
        <Chip type={chipOf(r.status)} label={r.status} />
        <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "monospace" }}>
          {r.orderId} · 建立者 {r.createdBy}
        </span>
      </div>
      <Block label="摘要" v={r.summary} />
      <Block label="結論" v={r.conclusion} />
      {r.attachments.length > 0 && (
        <Block label="附件" v={r.attachments.map((a) => a.name).join("、")} />
      )}
      {Object.keys(experimentData).length > 0 && (
        <div style={blockStyle}>
          <div style={blockLabelStyle}>實驗數據</div>
          {Object.entries(experimentData).map(([item, fields]) => (
            <div key={item} style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 700, marginBottom: 2 }}>{item}</div>
              {Object.entries(fields).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text3)" }}>{k}</span>
                  <span style={{ fontFamily: "monospace" }}>{v}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
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
        <div key={v.version} style={{ display: "flex", gap: 12, paddingBottom: 12 }}>
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
