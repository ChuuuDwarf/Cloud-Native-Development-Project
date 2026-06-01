"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface Props {
  onSuccess?: () => void;
}

interface DemoAccount {
  label: string;
  email: string;
  password: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  { label: "系統管理員", email: "admin@example.com", password: "Admin1234" },
  { label: "大主管", email: "director@example.com", password: "Direc1234" },
  { label: "LAB-A主管", email: "supervisor@example.com", password: "Super1234" },
  { label: "LAB-B主管", email: "supervisor2@example.com", password: "Super1234" },
  { label: "LAB-C主管", email: "supervisor3@example.com", password: "Super1234" },
  { label: "LAB-A人員", email: "engineer@example.com", password: "Engin1234" },
  { label: "LAB-B人員", email: "engineer2@example.com", password: "Engin1234" },
  { label: "LAB-C人員", email: "engineer3@example.com", password: "Engin1234" },
  { label: "廠區使用者", email: "requester@example.com", password: "Reque1234" },
];

export function LoginForm({ onSuccess }: Props) {
  const { login, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login({ email, password });
      onSuccess?.();
    } catch {
      // error is surfaced via AuthContext.error
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        width: "100%",
        maxWidth: 380,
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: 32,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div>
        <div
          style={{
            fontSize: 22,
            fontWeight: 800,
            background: "linear-gradient(135deg,#388bfd,#39d0d8)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            marginBottom: 4,
          }}
        >
          LIMS 登入
        </div>
        <div
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
            letterSpacing: 1,
          }}
        >
          LABORATORY INFORMATION MANAGEMENT SYSTEM
        </div>
      </div>

      <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ fontSize: 11, color: "var(--text2)" }}>快速登入 (測試帳號)</span>
        <select
          value={email}
          onChange={(e) => {
            const account = DEMO_ACCOUNTS.find((a) => a.email === e.target.value);
            if (account) {
              setEmail(account.email);
              setPassword(account.password);
            }
          }}
          style={inputStyle}
        >
          <option value="">— 選擇測試帳號 —</option>
          {DEMO_ACCOUNTS.map((a) => (
            <option key={a.email} value={a.email}>
              {a.label} ({a.email})
            </option>
          ))}
        </select>
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ fontSize: 11, color: "var(--text2)" }}>Email</span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          style={inputStyle}
          placeholder="admin@example.com"
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ fontSize: 11, color: "var(--text2)" }}>密碼</span>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          style={inputStyle}
          placeholder="••••••••"
        />
      </label>

      {error && (
        <div
          style={{
            background: "rgba(255,68,68,0.1)",
            border: "1px solid rgba(255,68,68,0.3)",
            borderRadius: 6,
            padding: "8px 12px",
            color: "var(--red)",
            fontSize: 12,
          }}
        >
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        style={{
          marginTop: 4,
          padding: "10px 16px",
          background: submitting ? "var(--s3)" : "linear-gradient(135deg,#388bfd,#39d0d8)",
          color: "#fff",
          fontWeight: 700,
          border: "none",
          borderRadius: 8,
          cursor: submitting ? "default" : "pointer",
          fontSize: 13,
        }}
      >
        {submitting ? "登入中..." : "登入"}
      </button>

      {process.env.NODE_ENV !== "production" && (
        <div
          style={{
            fontSize: 10,
            color: "var(--text3)",
            fontFamily: "monospace",
            lineHeight: 1.6,
            borderTop: "1px solid var(--border2)",
            paddingTop: 12,
          }}
        >
          DEV SEED ACCOUNTS:
          {DEMO_ACCOUNTS.map((a) => (
            <span key={a.email}>
              <br />
              {a.email} / {a.password}
            </span>
          ))}
        </div>
      )}
    </form>
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
};
