"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserStatusLabel } from "@/constants/status-labels";
import type { UserStatus } from "@/constants/enums";
import { useAuth } from "@/contexts/AuthContext";
import { masterDataApi } from "@/services/master-data-api";
import { userApi } from "@/services/user-api";
import type { CreateUserPayload, UserResponse } from "@/types/user";

export default function AccountPage() {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();

  const [keyword, setKeyword] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const canCreate = hasPermission("users:create");
  const canUpdate = hasPermission("users:update");

  const usersQuery = useQuery({
    queryKey: ["users", { keyword }],
    queryFn: () => userApi.list({ keyword: keyword || undefined, pageSize: 100 }),
  });

  const masterQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: () => masterDataApi.fetch(),
  });

  const toggleStatus = useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: UserStatus;
    }) => userApi.update(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          gap: 12,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>帳號管理</h1>
          <div
            style={{
              fontSize: 11,
              color: "var(--text3)",
              fontFamily: "monospace",
              letterSpacing: 2,
            }}
          >
            ACCOUNT MANAGEMENT · 使用者、角色與權限
          </div>
        </div>
        {canCreate && (
          <button onClick={() => setCreateOpen(true)} style={primaryBtn}>
            + 建立使用者
          </button>
        )}
      </header>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="搜尋名稱或 email"
          style={{ ...inputStyle, maxWidth: 280 }}
        />
      </div>

      <div
        style={{
          background: "var(--s1)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 13,
          }}
        >
          <thead>
            <tr style={{ background: "var(--s2)" }}>
              <Th>姓名</Th>
              <Th>Email</Th>
              <Th>角色</Th>
              <Th>狀態</Th>
              <Th>建立時間</Th>
              <Th style={{ textAlign: "right" }}>操作</Th>
            </tr>
          </thead>
          <tbody>
            {usersQuery.isLoading && (
              <tr>
                <Td colSpan={6} style={{ textAlign: "center", color: "var(--text3)" }}>
                  Loading…
                </Td>
              </tr>
            )}
            {usersQuery.isError && (
              <tr>
                <Td colSpan={6} style={{ textAlign: "center", color: "var(--red)" }}>
                  讀取失敗
                </Td>
              </tr>
            )}
            {usersQuery.data?.items.map((u) => (
              <UserRow
                key={u.id}
                user={u}
                canUpdate={canUpdate}
                onToggle={(next) =>
                  toggleStatus.mutate({ id: u.id, status: next })
                }
              />
            ))}
            {usersQuery.data?.items.length === 0 && (
              <tr>
                <Td colSpan={6} style={{ textAlign: "center", color: "var(--text3)" }}>
                  沒有符合條件的使用者
                </Td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {createOpen && (
        <CreateUserModal
          roles={masterQuery.data?.roles ?? []}
          labs={masterQuery.data?.labs ?? []}
          departments={masterQuery.data?.departments ?? []}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
            setCreateOpen(false);
          }}
        />
      )}
    </div>
  );
}

function UserRow({
  user,
  canUpdate,
  onToggle,
}: {
  user: UserResponse;
  canUpdate: boolean;
  onToggle: (next: UserStatus) => void;
}) {
  return (
    <tr style={{ borderTop: "1px solid var(--border2)" }}>
      <Td>{user.name}</Td>
      <Td>{user.email}</Td>
      <Td>
        {user.roles.length === 0 ? (
          <span style={{ color: "var(--text3)" }}>—</span>
        ) : (
          user.roles.map((r) => (
            <span key={r.id} style={roleBadge}>
              {r.name}
            </span>
          ))
        )}
      </Td>
      <Td>
        <StatusPill status={user.status} />
      </Td>
      <Td style={{ color: "var(--text3)", fontFamily: "monospace", fontSize: 11 }}>
        {new Date(user.createdAt).toLocaleString("zh-TW")}
      </Td>
      <Td style={{ textAlign: "right" }}>
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
      </Td>
    </tr>
  );
}

function StatusPill({ status }: { status: UserStatus }) {
  const isActive = status === "active";
  return (
    <span
      style={{
        background: isActive
          ? "rgba(63,185,80,0.15)"
          : "rgba(255,68,68,0.15)",
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

function CreateUserModal({
  roles,
  labs,
  departments,
  onClose,
  onCreated,
}: {
  roles: { id: string; name: string }[];
  labs: { id: string; code: string; name: string }[];
  departments: { id: string; code: string; name: string }[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<CreateUserPayload>({
    email: "",
    name: "",
    password: "",
    roleIds: [],
    labId: null,
    departmentId: null,
  });
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (payload: CreateUserPayload) => userApi.create(payload),
    onSuccess: () => onCreated(),
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })
          ?.response?.data?.error?.message ?? "建立失敗";
      setError(msg);
    },
  });

  return (
    <div
      role="dialog"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        zIndex: 100,
      }}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          create.mutate(form);
        }}
        style={{
          background: "var(--s1)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 24,
          width: "100%",
          maxWidth: 460,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 18 }}>建立使用者</h2>

        <Field label="姓名">
          <input
            required
            style={inputStyle}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </Field>
        <Field label="Email">
          <input
            required
            type="email"
            style={inputStyle}
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>
        <Field label="密碼 (≥8 字元)">
          <input
            required
            type="password"
            minLength={8}
            style={inputStyle}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>
        <Field label="角色">
          <select
            multiple
            size={Math.max(2, Math.min(roles.length, 4))}
            style={{ ...inputStyle, height: "auto" }}
            value={form.roleIds ?? []}
            onChange={(e) =>
              setForm({
                ...form,
                roleIds: Array.from(e.target.selectedOptions, (o) => o.value),
              })
            }
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="部門">
          <select
            style={inputStyle}
            value={form.departmentId ?? ""}
            onChange={(e) =>
              setForm({ ...form, departmentId: e.target.value || null })
            }
          >
            <option value="">— 未指定 —</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} · {d.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="實驗室">
          <select
            style={inputStyle}
            value={form.labId ?? ""}
            onChange={(e) =>
              setForm({ ...form, labId: e.target.value || null })
            }
          >
            <option value="">— 未指定 —</option>
            {labs.map((l) => (
              <option key={l.id} value={l.id}>
                {l.code} · {l.name}
              </option>
            ))}
          </select>
        </Field>

        {error && (
          <div
            style={{
              background: "rgba(255,68,68,0.1)",
              border: "1px solid rgba(255,68,68,0.3)",
              borderRadius: 6,
              padding: "6px 10px",
              color: "var(--red)",
              fontSize: 12,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" onClick={onClose} style={secondaryBtn}>
            取消
          </button>
          <button type="submit" disabled={create.isPending} style={primaryBtn}>
            {create.isPending ? "建立中…" : "建立"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, color: "var(--text2)" }}>{label}</span>
      {children}
    </label>
  );
}

function Th({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <th
      style={{
        textAlign: "left",
        padding: "10px 12px",
        fontSize: 11,
        letterSpacing: 1.5,
        color: "var(--text3)",
        fontFamily: "monospace",
        fontWeight: 600,
        ...style,
      }}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  colSpan,
  style,
}: {
  children: React.ReactNode;
  colSpan?: number;
  style?: React.CSSProperties;
}) {
  return (
    <td
      colSpan={colSpan}
      style={{ padding: "10px 12px", verticalAlign: "middle", ...style }}
    >
      {children}
    </td>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  color: "var(--text)",
  fontSize: 13,
  padding: "8px 12px",
  outline: "none",
  width: "100%",
};

const primaryBtn: React.CSSProperties = {
  padding: "8px 14px",
  background: "linear-gradient(135deg,#388bfd,#39d0d8)",
  color: "#fff",
  fontWeight: 700,
  border: "none",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: 12,
};

const secondaryBtn: React.CSSProperties = {
  padding: "6px 10px",
  background: "transparent",
  color: "var(--text2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 11,
};

const roleBadge: React.CSSProperties = {
  display: "inline-block",
  background: "rgba(56,139,253,0.15)",
  color: "var(--blue)",
  border: "1px solid rgba(56,139,253,0.4)",
  padding: "1px 8px",
  borderRadius: 8,
  fontSize: 10,
  marginRight: 4,
  fontFamily: "monospace",
};
