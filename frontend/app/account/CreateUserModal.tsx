"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { inputStyle, primaryBtn, secondaryBtn } from "@/constants/styles";
import { userApi } from "@/services/user-api";
import type { CreateUserPayload } from "@/types/user";

interface CreateUserModalProps {
  roles: { id: string; name: string }[];
  labs: { id: string; code: string; name: string }[];
  departments: { id: string; code: string; name: string }[];
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateUserModal({
  roles,
  labs,
  departments,
  onClose,
  onCreated,
}: CreateUserModalProps) {
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
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message ?? "建立失敗";
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
            onChange={(e) => setForm({ ...form, departmentId: e.target.value || null })}
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
            onChange={(e) => setForm({ ...form, labId: e.target.value || null })}
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, color: "var(--text2)" }}>{label}</span>
      {children}
    </label>
  );
}
