import type { ReactNode } from "react";
import { buttonStyle, modalHeaderStyle, modalOverlayStyle, modalStyle } from "../styles";

export function Modal({
  title,
  children,
  onClose,
  narrow = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  narrow?: boolean;
}) {
  return (
    <div style={modalOverlayStyle}>
      <div style={{ ...modalStyle, width: narrow ? "min(520px, 92vw)" : "min(900px, 94vw)" }}>
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
