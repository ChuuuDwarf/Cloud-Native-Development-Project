import { sampleStatusText } from "../constants";
import { statusBadgeStyle } from "../styles";

// Per-status tone overrides on the default blue badge. Mirrors the global
// Chip "rejected" tone (used by /execution for 已終止) so users see the
// same red across both pages.
const STATUS_TONE: Record<string, { background: string; color: string; border: string }> = {
  terminated: {
    background: "rgba(255,68,68,0.14)",
    color: "#ff4444",
    border: "1px solid rgba(255,68,68,0.35)",
  },
};

export function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONE[status];
  const style = tone ? { ...statusBadgeStyle, ...tone } : statusBadgeStyle;
  return <span style={style}>{sampleStatusText[status] ?? status}</span>;
}
