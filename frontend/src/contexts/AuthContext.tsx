"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi, type LoginPayload } from "@/services/auth-api";
import type { MeResponse } from "@/types/user";

interface AuthContextValue {
  user: MeResponse | null;
  isLoading: boolean;
  error: string | null;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (code: string) => boolean;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  // Start with isLoading=true so the gate shows a spinner until the first
  // /api/me call resolves; otherwise we'd flash the login form for users who
  // already have a valid cookie.
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMe = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 401) {
        setUser(null);
      } else {
        setError(
          (err as { message?: string })?.message ?? "Failed to fetch profile",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    await fetchMe();
  }, [fetchMe]);

  // Initial profile fetch on mount. fetchMe is async so setState only fires
  // after the network call resolves — not synchronously inside the effect
  // body. The rule's static analysis can't tell, so we suppress it here.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchMe();
  }, [fetchMe]);

  const login = useCallback(
    async (payload: LoginPayload) => {
      setError(null);
      try {
        await authApi.login(payload);
        await refresh();
      } catch (err: unknown) {
        const body = (
          err as { response?: { data?: { error?: { message?: string } } } }
        )?.response?.data?.error;
        setError(body?.message ?? "Login failed");
        throw err;
      }
    },
    [refresh],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const hasPermission = useCallback(
    (code: string) => {
      if (!user) return false;
      return user.permissions.includes("*") || user.permissions.includes(code);
    },
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, error, login, logout, hasPermission, refresh }),
    [user, isLoading, error, login, logout, hasPermission, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }
  return ctx;
}
