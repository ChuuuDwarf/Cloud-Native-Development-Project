"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  id: string;
  href: string;
  icon: string;
  label: string;
  permission?: string; // omit -> visible to every authenticated user
  badge?: number;
}

interface NavSection {
  section: string;
  items: NavItem[];
}

const nav: NavSection[] = [
  {
    section: "OVERVIEW",
    items: [
      {
        id: "dashboard",
        href: "/",
        icon: "⬛",
        label: "主管儀表板",
        permission: "dashboard:read",
      },
    ],
  },
  {
    section: "委託流程",
    items: [
      {
        id: "orders",
        href: "/orders",
        icon: "📋",
        label: "委託單管理",
        permission: "orders:read",
      },
      {
        id: "approve",
        href: "/approve",
        icon: "✅",
        label: "簽核管理",
        permission: "orders:approve",
      },
      {
        id: "sample",
        href: "/sample",
        icon: "🧪",
        label: "收樣管理",
        // Engineer's workflow page (mark samples as received, bind to WIPs).
        // plant_user still has `samples:read` so they can see sample status
        // inside their own order detail page, but shouldn't see this top-
        // level nav entry — gate by `samples:create` which only engineers
        // and supervisors hold.
        permission: "samples:create",
      },
      {
        id: "wip",
        href: "/wip",
        icon: "🔬",
        label: "分貨 / WIP",
        permission: "wips:read",
      },
    ],
  },
  {
    section: "執行與機台",
    items: [
      {
        id: "dispatch",
        href: "/dispatch",
        icon: "🗂️",
        label: "派工排程",
        permission: "dispatches:read",
      },
      {
        id: "machine",
        href: "/machine",
        icon: "⚙️",
        label: "機台管理",
        permission: "machines:read",
      },
      {
        id: "recipe",
        href: "/recipe",
        icon: "📐",
        label: "Recipe 管理",
        permission: "recipes:read",
      },
      {
        id: "transfer",
        href: "/transfer",
        icon: "🔄",
        label: "樣品交接",
        // Engineer-only workflow; see comment on `/sample` above.
        permission: "samples:create",
      },
      {
        id: "execution",
        href: "/execution",
        icon: "🧫",
        label: "實驗執行",
        permission: "experiment_runs:read",
      },
    ],
  },
  {
    section: "結案與倉儲",
    items: [
      {
        id: "report",
        href: "/report",
        icon: "📊",
        label: "實驗報告管理",
        permission: "reports:read",
      },
      {
        id: "closure",
        href: "/closure",
        icon: "📑",
        label: "結單管理",
        permission: "reports:read",
      },
      {
        id: "storage",
        href: "/storage",
        icon: "📦",
        label: "倉儲取件",
        permission: "storage_locations:read",
      },
      {
        id: "exception",
        href: "/exception",
        icon: "⚠️",
        label: "異常管理",
        permission: "issues:read",
      },
      {
        id: "alert",
        href: "/alert",
        icon: "🔔",
        label: "告警升級",
        permission: "issues:read",
      },
    ],
  },
  {
    section: "系統",
    items: [
      {
        id: "account",
        href: "/account",
        icon: "👥",
        label: "帳號管理",
        permission: "users:read",
      },
      {
        id: "config",
        href: "/config",
        icon: "🛠️",
        label: "系統設定",
        permission: "system_settings:read",
      },
    ],
  },
];

export default function Sidebar() {
  const [open, setOpen] = useState(true);
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, hasPermission } = useAuth();

  const visibleSections = nav
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (i) => !i.permission || hasPermission(i.permission),
      ),
    }))
    .filter((g) => g.items.length > 0);

  const initial = user?.name?.[0] ?? "?";

  async function handleLogout() {
    await logout();
    router.replace("/");
  }

  return (
    <aside
      style={{
        width: open ? 220 : 56,
        flexShrink: 0,
        background: "var(--s1)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "12px 0",
        gap: 2,
        transition: "width .25s",
        overflow: "hidden",
        height: "100vh",
        position: "sticky",
        top: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          width: "100%",
          padding: "0 12px 12px",
          borderBottom: "1px solid var(--border2)",
          marginBottom: 8,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            flexShrink: 0,
            background: "linear-gradient(135deg,#388bfd,#39d0d8)",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 800,
            color: "#fff",
            fontSize: 14,
          }}
        >
          LI
        </div>
        {open && <span style={{ fontWeight: 800, fontSize: 15 }}>LIMS</span>}
      </div>

      {/* Nav */}
      <div style={{ flex: 1, width: "100%", overflowY: "auto" }}>
        {visibleSections.map((group) => (
          <div
            key={group.section}
            style={{ width: "100%", padding: "4px 8px 0" }}
          >
            {open && (
              <div
                style={{
                  fontSize: 9,
                  letterSpacing: 2,
                  color: "var(--text3)",
                  padding: "8px 8px 4px",
                  fontFamily: "monospace",
                }}
              >
                {group.section}
              </div>
            )}
            {group.items.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  style={{ textDecoration: "none" }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: 8,
                      borderRadius: 8,
                      cursor: "pointer",
                      background: active
                        ? "rgba(56,139,253,0.15)"
                        : "transparent",
                      position: "relative",
                      minHeight: 36,
                      borderLeft: active
                        ? "3px solid var(--blue)"
                        : "3px solid transparent",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 16,
                        width: 24,
                        textAlign: "center",
                        color: active ? "var(--blue)" : "var(--text2)",
                      }}
                    >
                      {item.icon}
                    </span>
                    {open && (
                      <span
                        style={{
                          fontSize: 12.5,
                          color: active ? "var(--text)" : "var(--text2)",
                          flex: 1,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {item.label}
                      </span>
                    )}
                    {open && item.badge && (
                      <span
                        style={{
                          background: "var(--red)",
                          color: "#fff",
                          fontSize: 9,
                          padding: "1px 5px",
                          borderRadius: 10,
                          fontFamily: "monospace",
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Toggle */}
      <div
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "center",
          padding: 8,
          cursor: "pointer",
          color: "var(--text3)",
          borderTop: "1px solid var(--border2)",
        }}
      >
        {open ? "◀" : "▶"}
      </div>

      {/* Footer — user info + logout */}
      <div
        style={{
          width: "100%",
          padding: 8,
          borderTop: "1px solid var(--border2)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg,#1a5276,#388bfd)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
            fontWeight: 700,
            flexShrink: 0,
            color: "#fff",
          }}
        >
          {initial}
        </div>
        {open && (
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {user?.name ?? "—"}
            </div>
            <div
              style={{
                fontSize: 10,
                color: "var(--text3)",
                fontFamily: "monospace",
              }}
            >
              {user?.role ?? "—"}
            </div>
          </div>
        )}
        {open && user && (
          <button
            onClick={handleLogout}
            title="登出"
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text2)",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 10,
              padding: "4px 8px",
            }}
          >
            登出
          </button>
        )}
      </div>
    </aside>
  );
}
