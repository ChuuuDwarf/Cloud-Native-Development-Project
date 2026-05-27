"use client";
import { useState } from "react";
import Btn from "@/components/ui/Btn";
import Modal, { Field, inputStyle } from "@/components/ui/Modal";
import { reportsApi } from "@/services/reports-api";
import type { Report, RunFn } from "../types";

export default function EditModal({
  r,
  run,
  onClose,
}: {
  r: Report;
  run: RunFn;
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
                "報告已更新"
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
