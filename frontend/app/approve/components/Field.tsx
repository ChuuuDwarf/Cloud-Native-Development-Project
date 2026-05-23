import type { ReactNode } from "react";

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={{ display: "block", marginTop: 10 }}>
      <div style={{ fontSize: 12, color: "var(--text3)", marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}
