"use client";
import Modal from "@/components/ui/Modal";
import type { ClosureCheck } from "../types";
import { CONDITIONS_NOTE } from "../constants";
import { conditionRowStyle } from "../styles";

export default function ClosureConditionsModal({
  detail,
  onClose,
}: {
  detail: ClosureCheck;
  onClose: () => void;
}) {
  return (
    <Modal open title={`結單條件 · ${detail.orderId}`} onClose={onClose}>
      <p style={{ fontSize: 12, color: "var(--text3)", marginBottom: 14 }}>{CONDITIONS_NOTE}</p>
      {detail.conditions.map((cond, i) => (
        <div key={i} style={conditionRowStyle}>
          <span style={{ fontSize: 16 }}>{cond.ok ? "✅" : "⬜"}</span>
          <span style={{ color: cond.ok ? "var(--text)" : "var(--text3)" }}>{cond.name}</span>
        </div>
      ))}
    </Modal>
  );
}
