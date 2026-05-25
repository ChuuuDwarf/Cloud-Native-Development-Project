"use client";
import { ROLES, type Role } from "@/types/lab";

// 展示用角色切換器：操作 API 時帶入 X-Role，用來示範權限差異。
export default function RoleSwitcher({
  role,
  onChange,
}: {
  role: Role;
  onChange: (r: Role) => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span
        style={{ fontSize: 10, color: "var(--text3)", fontFamily: "monospace" }}
      >
        目前角色
      </span>
      <select
        value={role}
        onChange={(e) => onChange(e.target.value as Role)}
        style={{
          background: "var(--s2)",
          border: "1px solid var(--border)",
          color: "var(--text2)",
          padding: "6px 10px",
          borderRadius: 7,
          fontSize: 12,
          outline: "none",
          cursor: "pointer",
          fontFamily: "inherit",
        }}
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
    </div>
  );
}
