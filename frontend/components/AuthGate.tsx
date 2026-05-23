"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";
import { LoginForm } from "@/components/LoginForm";
import { useAuth } from "@/contexts/AuthContext";

function getDefaultRouteByRole(role?: string) {
  switch (role) {
    case "system_admin":
      return "/";

    case "lab_supervisor":
      return "/";

    case "lab_engineer":
      return "/sample";

    case "plant_user":
      return "/orders";

    default:
      return "/orders";
  }
}

const routeRoleRules: Array<{
  path: string;
  exact?: boolean;
  allowedRoles: string[];
}> = [
  {
    path: "/",
    exact: true,
    allowedRoles: ["system_admin", "lab_supervisor"],
  },
  {
    path: "/approve",
    allowedRoles: ["system_admin", "lab_supervisor"],
  },
  {
    path: "/account",
    allowedRoles: ["system_admin"],
  },
  {
    path: "/config",
    allowedRoles: ["system_admin"],
  },
  {
    path: "/sample",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/wip",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/dispatch",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/machine",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/recipe",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/transfer",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/storage",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/exception",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/alert",
    allowedRoles: ["system_admin", "lab_supervisor", "lab_engineer"],
  },
  {
    path: "/orders",
    allowedRoles: ["system_admin", "plant_user"],
  },
];

function getAllowedRolesForPath(pathname: string) {
  const rule = routeRoleRules.find((rule) => {
    if (rule.exact) {
      return pathname === rule.path;
    }

    return pathname === rule.path || pathname.startsWith(`${rule.path}/`);
  });

  return rule?.allowedRoles;
}

export function AuthGate({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const allowedRoles = getAllowedRolesForPath(pathname);

  const isForbidden =
    !!user &&
    !!allowedRoles &&
    !allowedRoles.includes(user.role);

  useEffect(() => {
    if (isLoading) return;

    if (user && pathname === "/login") {
      router.replace(getDefaultRouteByRole(user.role));
      return;
    }

    if (isForbidden) {
      router.replace(getDefaultRouteByRole(user.role));
    }
  }, [user, isLoading, pathname, isForbidden, router]);

  if (isLoading) {
    return (
      <div style={fillScreen}>
        <div
          style={{
            fontSize: 12,
            color: "var(--text3)",
            fontFamily: "monospace",
            letterSpacing: 2,
          }}
        >
          LOADING…
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={fillScreen}>
        <LoginForm />
      </div>
    );
  }

  if (pathname === "/login" || isForbidden) {
    return (
      <div style={fillScreen}>
        <div
          style={{
            fontSize: 12,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          REDIRECTING…
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 24,
          background: "var(--bg)",
        }}
      >
        {children}
      </main>
    </div>
  );
}

const fillScreen: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: "100vh",
  background: "var(--bg)",
  padding: 16,
};