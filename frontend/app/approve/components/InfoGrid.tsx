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
