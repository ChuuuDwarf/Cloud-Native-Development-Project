import { UserStatusLabel } from "@/constants/status-labels";
import { roleBadge, secondaryBtn } from "@/constants/styles";
import type { UserStatus } from "@/constants/enums";
import type { UserResponse } from "@/types/user";

interface UserRowProps {
  user: UserResponse;
  canUpdate: boolean;
  onToggle: (next: UserStatus) => void;
}

export default function UserRow({ user, canUpdate, onToggle }: UserRowProps) {
  return (
    <tr style={{ borderTop: "1px solid var(--border2)" }}>
      <td style={cellStyle}>{user.name}</td>
      <td style={cellStyle}>{user.email}</td>
      <td style={cellStyle}>
        {user.roles.length === 0 ? (
          <span style={{ color: "var(--text3)" }}>—</span>
        ) : (
          user.roles.map((r) => (
            <span key={r.id} style={roleBadge}>
              {r.name}
            </span>
          ))
        )}
      </td>
      <td style={cellStyle}>
        <StatusPill status={user.status} />
      </td>
      <td
        style={{
          ...cellStyle,
          color: "var(--text3)",
          fontFamily: "monospace",
          fontSize: 11,
        }}
      >
        {new Date(user.createdAt).toLocaleString("zh-TW")}
      </td>
      <td style={{ ...cellStyle, textAlign: "right" }}>
        {canUpdate && (
          <button
            style={{
              ...secondaryBtn,
              color: user.isActive ? "var(--red)" : "var(--green)",
            }}
            onClick={() => onToggle(user.isActive ? "disabled" : "active")}
          >
            {user.isActive ? "停用" : "啟用"}
          </button>
        )}
      </td>
    </tr>
  );
}

function StatusPill({ status }: { status: UserStatus }) {
  const isActive = status === "active";
  return (
    <span
      style={{
        background: isActive ? "rgba(63,185,80,0.15)" : "rgba(255,68,68,0.15)",
        color: isActive ? "var(--green)" : "var(--red)",
        border: `1px solid ${isActive ? "rgba(63,185,80,0.4)" : "rgba(255,68,68,0.4)"}`,
        padding: "2px 8px",
        borderRadius: 10,
        fontSize: 11,
        fontFamily: "monospace",
      }}
    >
      {UserStatusLabel[status]}
    </span>
  );
}

const cellStyle: React.CSSProperties = {
  padding: "10px 12px",
  verticalAlign: "middle",
};
