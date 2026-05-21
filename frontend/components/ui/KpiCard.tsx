export default function KpiCard({
  label,
  value,
  sub,
  color,
  icon,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color: string;
  icon?: string;
}) {
  return (
    <div
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border2)",
        borderRadius: 12,
        padding: 18,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: `linear-gradient(90deg, ${color}, transparent)`,
        }}
      />
      {icon && (
        <div
          style={{
            position: "absolute",
            right: 14,
            top: 14,
            fontSize: 20,
            opacity: 0.2,
          }}
        >
          {icon}
        </div>
      )}
      <div
        style={{
          fontSize: 10,
          color: "var(--text3)",
          letterSpacing: 2,
          fontFamily: "monospace",
          marginBottom: 10,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: -1, color }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 6 }}>
          {sub}
        </div>
      )}
    </div>
  );
}
