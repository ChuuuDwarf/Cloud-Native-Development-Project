import type { ReactNode } from "react";
import { panelStyle, panelTitleStyle } from "../styles";

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {children}
    </section>
  );
}
