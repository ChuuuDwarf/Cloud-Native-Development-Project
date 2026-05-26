import type { ReactNode } from "react";
import { statusLabel } from "../constants";
import {
  buttonStyle,
  inputStyle,
  modalHeaderStyle,
  modalOverlayStyle,
  modalStyle,
  panelStyle,
  panelTitleStyle,
  statusBadgeStyle,
} from "../styles";
import type { OrderStatus } from "../types";

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {children}
    </section>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={{ display: "block", marginTop: 10 }}>
      <div style={{ fontSize: 12, color: "var(--text3)", marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}

export function Input({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <input
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      style={{
        ...inputStyle,
        opacity: disabled ? 0.65 : 1,
        cursor: disabled ? "not-allowed" : "text",
      }}
    />
  );
}

export function StatusBadge({ status }: { status: OrderStatus }) {
  // Fallback to the raw value so an unmapped (e.g. future cross-module) status
  // never renders as a blank badge.
  return <span style={statusBadgeStyle}>{statusLabel[status] ?? status}</span>;
}

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div style={modalOverlayStyle}>
      <div style={modalStyle}>
        <div style={modalHeaderStyle}>
          <h3 style={{ margin: 0, fontSize: 17 }}>{title}</h3>
          <button type="button" onClick={onClose} style={buttonStyle("red")}>
            關閉
          </button>
        </div>
        <div style={{ padding: 18, overflowY: "auto" }}>{children}</div>
      </div>
    </div>
  );
}

export function InfoGrid({ rows }: { rows: [string, string][] }) {
  return (
    <div
      style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "8px 12px", fontSize: 13 }}
    >
      {rows.map(([label, value]) => (
        <div key={label} style={{ display: "contents" }}>
          <div style={{ color: "var(--text3)", fontWeight: 700 }}>{label}</div>
          <div style={{ color: "var(--text)" }}>{value || "-"}</div>
        </div>
      ))}
    </div>
  );
}
