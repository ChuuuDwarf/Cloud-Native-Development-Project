import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock next/navigation. `pathname` is read by AuthGate; tests override it
// via the pathnameRef wrapper.
const pathnameRef = { current: "/" };
vi.mock("next/navigation", () => ({
  usePathname: () => pathnameRef.current,
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

// Mock useAuth so we don't need a real AuthProvider.
const useAuthMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

// Sidebar pulls in next/link and css vars — render it as a stub so we can
// assert AuthGate's branch logic in isolation.
vi.mock("@/components/Sidebar", () => ({
  default: () => <aside data-testid="sidebar-stub">SIDEBAR</aside>,
}));

import { AuthGate } from "@/components/AuthGate";

describe("AuthGate", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    pathnameRef.current = "/";
  });

  it("renders LOADING placeholder while auth is loading", () => {
    useAuthMock.mockReturnValue({
      user: null,
      isLoading: true,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      hasPermission: () => false,
    });

    render(
      <AuthGate>
        <div>protected child</div>
      </AuthGate>,
    );

    expect(screen.getByText(/LOADING/)).toBeInTheDocument();
    expect(screen.queryByText("protected child")).not.toBeInTheDocument();
    expect(screen.queryByTestId("sidebar-stub")).not.toBeInTheDocument();
  });

  it("renders the LoginForm when not authenticated", () => {
    useAuthMock.mockReturnValue({
      user: null,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      hasPermission: () => false,
    });

    render(
      <AuthGate>
        <div>protected child</div>
      </AuthGate>,
    );

    // LoginForm renders this placeholder
    expect(screen.getByPlaceholderText("admin@example.com")).toBeInTheDocument();
    expect(screen.queryByText("protected child")).not.toBeInTheDocument();
    expect(screen.queryByTestId("sidebar-stub")).not.toBeInTheDocument();
  });

  it("renders Sidebar + children when authenticated on a normal route", () => {
    useAuthMock.mockReturnValue({
      user: {
        id: "u-admin",
        name: "Admin",
        email: "admin@example.com",
        role: "system_admin",
        permissions: ["*"],
        labId: null,
        departmentId: null,
      },
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      hasPermission: (c: string) => c === "*" || true,
    });
    pathnameRef.current = "/orders";

    render(
      <AuthGate>
        <div>protected child</div>
      </AuthGate>,
    );

    expect(screen.getByTestId("sidebar-stub")).toBeInTheDocument();
    expect(screen.getByText("protected child")).toBeInTheDocument();
  });

  it("on /login while authenticated, renders REDIRECTING placeholder", () => {
    useAuthMock.mockReturnValue({
      user: {
        id: "u-admin",
        name: "Admin",
        email: "admin@example.com",
        role: "system_admin",
        permissions: ["*"],
        labId: null,
        departmentId: null,
      },
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      hasPermission: () => true,
    });
    pathnameRef.current = "/login";

    render(
      <AuthGate>
        <div>protected child</div>
      </AuthGate>,
    );

    expect(screen.getByText(/REDIRECTING/)).toBeInTheDocument();
    expect(screen.queryByText("protected child")).not.toBeInTheDocument();
    expect(screen.queryByTestId("sidebar-stub")).not.toBeInTheDocument();
  });
});
