"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

/**
 * /login is a thin route — the AuthGate in app/layout.tsx already shows the
 * login form whenever the user isn't authenticated. This page exists so that
 * `<Link href="/login">` deep links work and `router.push("/login")` from a
 * logout button has somewhere to land.
 *
 * If the user is already logged in, bounce them back to `/`.
 */
export default function LoginPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/");
    }
  }, [user, isLoading, router]);

  // The form is rendered by AuthGate itself when !user, so this page returns
  // nothing visible — AuthGate already paints the centered LoginForm.
  return null;
}
