"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UserStatus } from "@/constants/enums";
import { inputStyle, primaryBtn } from "@/constants/styles";
import { useAuth } from "@/contexts/AuthContext";
import { masterDataApi } from "@/services/master-data-api";
import { userApi } from "@/services/user-api";
import CreateUserModal from "./CreateUserModal";
import UserRow from "./UserRow";

export default function AccountPage() {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();

  const [keyword, setKeyword] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const canCreate = hasPermission("users:create");
  const canUpdate = hasPermission("users:update");

  const usersQuery = useQuery({
    queryKey: ["users", { keyword }],
    queryFn: () =>
      userApi.list({ keyword: keyword || undefined, pageSize: 100 }),
  });

  const masterQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: () => masterDataApi.fetch(),
  });

  const toggleStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: UserStatus }) =>
      userApi.update(id, { status }),
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
                <Td
                  colSpan={6}
                  style={{ textAlign: "center", color: "var(--text3)" }}
                >
                  Loading…
                </Td>
              </tr>
            )}
            {usersQuery.isError && (
              <tr>
                <Td
                  colSpan={6}
                  style={{ textAlign: "center", color: "var(--red)" }}
                >
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
                <Td
                  colSpan={6}
                  style={{ textAlign: "center", color: "var(--text3)" }}
                >
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
