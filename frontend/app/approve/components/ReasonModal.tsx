"use client";

import type { Dispatch, SetStateAction } from "react";
import type { ReasonModalState } from "../types";
import { buttonStyle, textareaStyle } from "../styles";
import { Modal } from "./Modal";

export function ReasonModal({
  state,
  setState,
  onSubmit,
}: {
  state: Extract<ReasonModalState, { open: true }>;
  setState: Dispatch<SetStateAction<ReasonModalState>>;
  onSubmit: () => void;
}) {
  return (
    <Modal title={state.title} onClose={() => setState({ open: false })} narrow>
      <p style={{ color: "var(--text2)", fontSize: 13, lineHeight: 1.7, marginBottom: 12 }}>
        {state.hint}
      </p>

      <textarea
        value={state.value}
        onChange={(event) =>
          setState((current) =>
            current.open ? { ...current, value: event.target.value } : current
          )
        }
        placeholder="請輸入原因..."
        style={textareaStyle}
      />

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
        <button type="button" onClick={() => setState({ open: false })} style={buttonStyle("gray")}>
          取消
        </button>

        <button type="button" onClick={onSubmit} style={buttonStyle("blue")}>
          確認送出
        </button>
      </div>
    </Modal>
  );
}
