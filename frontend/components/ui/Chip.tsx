type ChipType =
  | "draft"
  | "pending"
  | "review"
  | "approved"
  | "running"
  | "done"
  | "rejected"
  | "paused"
  | "idle";

const styles: Record<ChipType, { bg: string; color: string }> = {
  draft: { bg: "rgba(139,148,158,0.12)", color: "#8b949e" },
  pending: { bg: "rgba(227,179,65,0.12)", color: "#e3b341" },
  review: { bg: "rgba(188,140,255,0.12)", color: "#bc8cff" },
  approved: { bg: "rgba(56,139,253,0.12)", color: "#388bfd" },
  running: { bg: "rgba(57,208,216,0.12)", color: "#39d0d8" },
  done: { bg: "rgba(63,185,80,0.12)", color: "#3fb950" },
  rejected: { bg: "rgba(255,68,68,0.12)", color: "#ff4444" },
  paused: { bg: "rgba(247,129,102,0.12)", color: "#f78166" },
  idle: { bg: "rgba(139,148,158,0.1)", color: "#3d4a56" },
};

export default function Chip({
  type,
  label,
}: {
  type: ChipType;
  label: string;
}) {
  const s = styles[type];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: 10,
        fontWeight: 600,
        padding: "3px 9px",
        borderRadius: 20,
        background: s.bg,
        color: s.color,
        fontFamily: "monospace",
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: s.color,
          flexShrink: 0,
        }}
      />
      {label}
    </span>
  );
}
