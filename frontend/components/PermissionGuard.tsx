"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface PermissionGuardProps {
  requiredPermission: string;
  children: React.ReactNode;
  redirectTo?: string;
  redirectDelayMs?: number;
}

export function PermissionGuard({
  requiredPermission,
  children,
  redirectTo = "/",
  redirectDelayMs = 2000,
}: PermissionGuardProps) {
  const { hasPermission, isLoading } = useAuth();
  const router = useRouter();
  const allowed = hasPermission(requiredPermission);

  useEffect(() => {
    if (!isLoading && !allowed) {
      const timer = setTimeout(() => {
        router.replace(redirectTo);
      }, redirectDelayMs);
      return () => clearTimeout(timer);
    }
  }, [isLoading, allowed, router, redirectTo, redirectDelayMs]);

  if (isLoading) {
    return <div>...loading...</div>;
  }

  if (!allowed) {
    return (
      <div style={{ padding: 24 }}>
        <h2 style={{ color: "var(--text)", margin: 0 }}>無權限存取此頁面</h2>
        <p style={{ color: "var(--text2)", marginTop: 8 }}>
          {Math.ceil(redirectDelayMs / 1000)} 秒後將返回首頁，或
          <a href={redirectTo} style={{ color: "var(--blue)", marginLeft: 4 }}>
            立即返回
          </a>
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
