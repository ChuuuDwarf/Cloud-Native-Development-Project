"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";
import { LoginForm } from "@/components/LoginForm";
import { useAuth } from "@/contexts/AuthContext";

/**
 * Decides what the user actually sees:
 *
 * - Loading initial /api/me probe -> centered spinner placeholder
 * - Not authenticated -> full-screen login form (Sidebar suppressed)
 * - Authenticated -> Sidebar + <main>{children}</main>
 *
 * The /login route is allowed through even when unauthenticated, so a logged-
 * out user landing on /login sees the form without redirect loops.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();

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

  // The /login route is a no-op once authenticated — render the same authed
  // shell so the deep link doesn't 404, but the page itself is just a redirect.
  if (pathname === "/login") {
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
