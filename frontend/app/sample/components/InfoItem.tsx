import type { ReactNode } from "react";
import { infoItemStyle, infoLabelStyle, infoValueStyle } from "../styles";

export function InfoItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div style={infoItemStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  );
}
