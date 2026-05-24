"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { masterDataApi } from "@/services/master-data-api";

type RoleName = "system_admin" | "lab_supervisor" | "lab_engineer" | "plant_user";

interface NavItem {
  id: string;
  href: string;
  icon: string;
  label: string;
  roles?: RoleName[]; // omit -> 所有已登入使用者都看得到
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
        roles: ["system_admin", "lab_supervisor"],
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
        roles: ["plant_user"],
      },
      {
        id: "approve",
        href: "/approve",
        icon: "✅",
        label: "簽核管理",
        roles: ["system_admin", "lab_supervisor"],
      },
      {
        id: "sample",
        href: "/sample",
        icon: "🧪",
        label: "收樣管理",
        // Lab users receive samples here; plant users track samples created
        // after confirming delivery from orders.
        roles: ["system_admin", "lab_engineer", "lab_supervisor", "plant_user"],
      },
      {
        id: "wip",
        href: "/wip",
        icon: "🔬",
        label: "分貨 / WIP",
        roles: ["system_admin", "lab_engineer", "lab_supervisor"],
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
        roles: ["system_admin", "lab_engineer", "lab_supervisor"],
      },
      {
        id: "machine",
        href: "/machine",
        icon: "⚙️",
        label: "機台管理",
        roles: ["system_admin", "lab_engineer", "lab_supervisor"],
      },
      {
        id: "recipe",
        href: "/recipe",
        icon: "📐",
        label: "Recipe 管理",
        roles: ["system_admin", "lab_engineer", "lab_supervisor"],
      },
      {
        id: "transfer",
        href: "/transfer",
        icon: "🔄",
        label: "樣品交接",
        // Engineer-only workflow; see comment on `/sample` above.
        roles: ["system_admin", "lab_engineer", "lab_supervisor"],
      },
    ],
  },
  {
    section: "結案與倉儲",
    items: [
      {
        id: "storage",
        href: "/storage",
        icon: "📦",
        label: "倉儲取件",
        roles: ["system_admin", "lab_engineer", "lab_supervisor"],
      },
      {
        id: "exception",
        href: "/exception",
        icon: "⚠️",
        label: "異常管理",
        roles: ["system_admin", "lab_supervisor", "lab_engineer"],
      },
      {
        id: "alert",
        href: "/alert",
        icon: "🔔",
        label: "告警升級",
        roles: ["system_admin", "lab_supervisor", "lab_engineer"],
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
        roles: ["system_admin"],
      },
      {
        id: "config",
        href: "/config",
        icon: "🛠️",
        label: "系統設定",
        roles: ["system_admin"],
      },
      {
        id: "others",
        href: "/others",
        icon: "",
        label: "替代",
        roles: ["system_admin"]
      }
    ],
  },
];

export default function Sidebar() {
  const [open, setOpen] = useState(true);
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const masterQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: masterDataApi.fetch,
  });

  const currentLab = masterQuery.data?.labs.find((lab) => lab.id === user?.labId);
  const roleLabelMap: Record<string, string> = {
    system_admin: "系統管理者",
    lab_supervisor: "實驗室主管",
    lab_engineer: "實驗室人員",
    plant_user: "廠區使用者",
  };

  const roleLabel = user?.role ? (roleLabelMap[user.role] ?? user.role) : "—";

  const userPositionLabel = currentLab ? `${currentLab.code} / ${roleLabel}` : roleLabel;

  const visibleSections = nav
    .map((g) => ({
      ...g,
      items: g.items.filter((item) => {
        if (!item.roles) return true;
        if (!user?.role) return false;

        return item.roles.includes(user.role as RoleName);
      }),
    }))
    .filter((g) => g.items.length > 0);

  const initial = user?.name?.[0] ?? "?";

  async function handleLogout() {
    await logout();
    router.replace("/");
  }

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(`${href}/`);
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
          <div key={group.section} style={{ width: "100%", padding: "4px 8px 0" }}>
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
              const active = isActive(item.href);
              const itemLabel =
                item.id === "sample" && user?.role === "plant_user" ? "樣品追蹤" : item.label;

              return (
                <Link key={item.id} href={item.href} style={{ textDecoration: "none" }}>
                  <div
                    title={!open ? itemLabel : undefined}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: 8,
                      borderRadius: 8,
                      cursor: "pointer",
                      background: active ? "rgba(56,139,253,0.15)" : "transparent",
                      position: "relative",
                      minHeight: 36,
                      borderLeft: active ? "3px solid var(--blue)" : "3px solid transparent",
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
                        {itemLabel}
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
                whiteSpace: "nowrap",
              }}
            >
              {userPositionLabel}
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
