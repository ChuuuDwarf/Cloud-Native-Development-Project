import type { ReactNode } from "react";

export default function Panel({
  title,
  tag,
  action,
  children,
  noPad,
}: {
  title: string;
  tag?: string;
  action?: ReactNode;
  children: ReactNode;
  noPad?: boolean;
}) {
  return (
    <div
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border2)",
        borderRadius: 12,
        overflow: "hidden",
        marginBottom: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "14px 18px",
          borderBottom: "1px solid var(--border2)",
          gap: 10,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 13, flex: 1 }}>{title}</span>
        {tag && (
          <span
            style={{
              fontSize: 10,
              fontFamily: "monospace",
              color: "var(--text3)",
              background: "var(--s3)",
              padding: "2px 7px",
              borderRadius: 4,
            }}
          >
            {tag}
          </span>
        )}
        {action}
      </div>
      <div style={noPad ? undefined : { padding: 0 }}>{children}</div>
    </div>
  );
}
