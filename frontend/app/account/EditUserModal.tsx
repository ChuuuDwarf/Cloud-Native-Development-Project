"use client";

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import type { UserStatus } from "@/constants/enums";
import { ROLES_WITHOUT_LAB, RoleLabel, type RoleName } from "@/constants/status-labels";
import { inputStyle, primaryBtn, secondaryBtn } from "@/constants/styles";
import { userApi } from "@/services/user-api";
import type { UpdateUserPayload, UserResponse } from "@/types/user";

interface EditUserModalProps {
  user: UserResponse;
  roles: { id: string; name: string }[];
  labs: { id: string; code: string; name: string }[];
  departments: { id: string; code: string; name: string }[];
  onClose: () => void;
  onSaved?: () => void;
}

interface EditFormState {
  name: string;
  phoneNumber: string;
  password: string;
  status: UserStatus;
  roleIds: string[];
  departmentId: string | null;
  labId: string | null;
}

function buildInitialState(user: UserResponse): EditFormState {
  return {
    name: user.name,
    phoneNumber: user.phoneNumber ?? "",
    password: "",
    status: user.status,
    roleIds: user.roles.map((r) => r.id),
    departmentId: user.departmentId,
    labId: user.labId,
  };
}

export default function EditUserModal({
  user,
  roles,
  labs,
  departments,
  onClose,
  onSaved,
}: EditUserModalProps) {
  const initial = buildInitialState(user);
  const [form, setForm] = useState<EditFormState>(initial);
  const [error, setError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);

  const roleNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const r of roles) map.set(r.id, r.name);
    return map;
  }, [roles]);

  const selectedRoleNames = form.roleIds
    .map((id) => roleNameById.get(id))
    .filter(Boolean) as string[];
  const showLabField =
    selectedRoleNames.length === 0 ||
    selectedRoleNames.some((n) => !ROLES_WITHOUT_LAB.has(n as RoleName));

  const update = useMutation({
    mutationFn: (payload: UpdateUserPayload) => userApi.update(user.id, payload),
    onSuccess: () => {
      onSaved?.();
      onClose();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message ?? "更新失敗";
      setError(msg);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setPhoneError(null);

    const trimmedPhone = form.phoneNumber.trim();
    if (trimmedPhone.length > 0 && trimmedPhone.length !== 10) {
      setPhoneError("電話需為 10 位數字");
      return;
    }

    // Diff against initial values so unchanged fields aren't sent (avoids
    // accidentally clobbering server-side state with stale local values).
    const payload: UpdateUserPayload = {};

    if (form.name !== initial.name) payload.name = form.name;
    if (form.status !== initial.status) payload.status = form.status;
    if (form.departmentId !== initial.departmentId) payload.departmentId = form.departmentId;

    // labId handling: when the role doesn't take a lab, force-clear (null) if the
    // user previously had one; otherwise omit. Else diff normally.
    if (!showLabField) {
      if (initial.labId !== null) payload.labId = null;
    } else if (form.labId !== initial.labId) {
      payload.labId = form.labId;
    }

    if (trimmedPhone !== (initial.phoneNumber ?? "").trim()) {
      payload.phoneNumber = trimmedPhone;
    }

    const sortedNext = [...form.roleIds].sort();
    const sortedInitial = [...initial.roleIds].sort();
    const rolesChanged =
      sortedNext.length !== sortedInitial.length ||
      sortedNext.some((id, i) => id !== sortedInitial[i]);
    if (rolesChanged) payload.roleIds = form.roleIds;

    if (form.password.length > 0) payload.password = form.password;

    if (Object.keys(payload).length === 0) {
      onClose();
      return;
    }
    update.mutate(payload);
  };

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
        onSubmit={handleSubmit}
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
        <h2 style={{ margin: 0, fontSize: 18 }}>編輯使用者</h2>
        <div
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
            marginTop: -6,
          }}
        >
          {user.email}
        </div>

        <Field label="姓名">
          <input
            required
            style={inputStyle}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </Field>
        <Field label="電話">
          <input
            type="tel"
            inputMode="numeric"
            maxLength={10}
            pattern="\d{10}"
            placeholder="例:0912345678"
            style={inputStyle}
            value={form.phoneNumber}
            onChange={(e) => {
              const cleaned = e.target.value.replace(/\D/g, "").slice(0, 10);
              setForm({ ...form, phoneNumber: cleaned });
              if (phoneError) setPhoneError(null);
            }}
          />
          {phoneError && (
            <span style={{ fontSize: 11, color: "var(--red)" }}>{phoneError}</span>
          )}
        </Field>
        <Field label="(可選) 修改密碼">
          <input
            type="password"
            minLength={8}
            placeholder="留白則維持原密碼"
            style={inputStyle}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>
        <Field label="狀態">
          <select
            style={inputStyle}
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value as UserStatus })}
          >
            <option value="active">啟用</option>
            <option value="disabled">停用</option>
          </select>
        </Field>
        <Field label="角色">
          <select
            multiple
            size={Math.max(2, Math.min(roles.length, 4))}
            style={{ ...inputStyle, height: "auto" }}
            value={form.roleIds}
            onChange={(e) => {
              const nextRoleIds = Array.from(e.target.selectedOptions, (o) => o.value);
              const nextNames = nextRoleIds
                .map((id) => roleNameById.get(id))
                .filter(Boolean) as string[];
              const nextShowLab =
                nextNames.length === 0 ||
                nextNames.some((n) => !ROLES_WITHOUT_LAB.has(n as RoleName));
              setForm({
                ...form,
                roleIds: nextRoleIds,
                labId: nextShowLab ? form.labId : null,
              });
            }}
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {RoleLabel[r.name as RoleName] ?? r.name}
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
        {showLabField && (
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
        )}

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
          <button type="submit" disabled={update.isPending} style={primaryBtn}>
            {update.isPending ? "儲存中…" : "儲存"}
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
