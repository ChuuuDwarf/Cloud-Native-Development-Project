import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";

const meMock = vi.fn();
const loginMock = vi.fn();
const logoutMock = vi.fn();
vi.mock("@/services/auth-api", () => ({
  authApi: {
    me: (...a: unknown[]) => meMock(...a),
    login: (...a: unknown[]) => loginMock(...a),
    logout: (...a: unknown[]) => logoutMock(...a),
  },
}));

import { AuthProvider, useAuth } from "@/contexts/AuthContext";

function Probe() {
  const { user, isLoading, error, hasPermission } = useAuth();
  if (isLoading) return <div>loading</div>;
  if (error) return <div>error:{error}</div>;
  return (
    <div>
      <div data-testid="user">{user?.email ?? "anon"}</div>
      <div data-testid="canRead">{String(hasPermission("orders:read"))}</div>
      <div data-testid="wildcard">{String(hasPermission("anything"))}</div>
    </div>
  );
}

const fakeMe = {
  id: "u-1",
  name: "A",
  email: "a@b.c",
  role: "system_admin",
  permissions: ["*"],
  labId: null,
  departmentId: null,
};

describe("AuthContext", () => {
  beforeEach(() => {
    meMock.mockReset();
    loginMock.mockReset();
    logoutMock.mockReset();
  });

  it("settles to user=null on 401 from /me", async () => {
    meMock.mockRejectedValue({ response: { status: 401 } });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("anon");
    });
    expect(screen.getByTestId("canRead")).toHaveTextContent("false");
  });

  it("loads user from /me on mount and grants wildcard permission", async () => {
    meMock.mockResolvedValue(fakeMe);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("a@b.c");
    });
    expect(screen.getByTestId("canRead")).toHaveTextContent("true");
    expect(screen.getByTestId("wildcard")).toHaveTextContent("true");
  });

  it("surfaces non-401 fetchMe errors via error state", async () => {
    meMock.mockRejectedValue(new Error("kaboom"));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/error:kaboom/)).toBeInTheDocument();
    });
  });

  it("login() calls authApi.login then refresh, and surfaces backend error message on failure", async () => {
    meMock.mockResolvedValue(fakeMe);
    loginMock.mockRejectedValueOnce({
      response: { data: { error: { message: "bad creds" } } },
    });

    function LoginProbe() {
      const { login, error } = useAuth();
      return (
        <div>
          <button
            onClick={() => {
              void login({ email: "x", password: "y" }).catch(() => {});
            }}
          >
            do-login
          </button>
          <div data-testid="err">{error ?? ""}</div>
        </div>
      );
    }

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText("do-login").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("err")).toHaveTextContent("bad creds");
    });
  });

  it("logout() clears the user even when authApi.logout throws", async () => {
    meMock.mockResolvedValue(fakeMe);
    logoutMock.mockRejectedValue(new Error("network down"));

    function LogoutProbe() {
      const { user, logout } = useAuth();
      return (
        <div>
          <div data-testid="user">{user?.email ?? "anon"}</div>
          <button
            onClick={() => {
              // logout's try/finally re-throws; swallow here so the test
              // doesn't surface an unhandled rejection.
              logout().catch(() => {});
            }}
          >
            do-logout
          </button>
        </div>
      );
    }

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("a@b.c");
    });
    await act(async () => {
      screen.getByText("do-logout").click();
    });
    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("anon");
    });
  });
});
