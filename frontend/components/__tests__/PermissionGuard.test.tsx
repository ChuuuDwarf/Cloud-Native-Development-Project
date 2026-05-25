import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const useAuthMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

import { PermissionGuard } from "../PermissionGuard";

describe("PermissionGuard", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    replaceMock.mockReset();
  });

  it("renders loading state and does not redirect while auth is loading", () => {
    useAuthMock.mockReturnValue({
      hasPermission: () => false,
      isLoading: true,
    });

    render(
      <PermissionGuard requiredPermission="user:read">
        <div>protected child</div>
      </PermissionGuard>,
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(screen.queryByText("protected child")).not.toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("renders user has permissions should be able to see children", () => {
    useAuthMock.mockReturnValue({
      hasPermission: () => true,
      isLoading: false,
    });

    render(
      <PermissionGuard requiredPermission="user:read">
        <div>protected child</div>
      </PermissionGuard>,
    );

    expect(screen.getByText("protected child")).toBeInTheDocument();
    expect(screen.queryByText(/無權限/)).not.toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("renders user has no permissions should be able to see children", () => {
    useAuthMock.mockReturnValue({
      hasPermission: () => false,
      isLoading: false,
    });

    render(
      <PermissionGuard requiredPermission="user:read">
        <div>protected child</div>
      </PermissionGuard>,
    );

    expect(screen.getByText(/無權限/)).toBeInTheDocument();
    expect(screen.queryByText("protexted child")).not.toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects to homepage after delay when user has no permission", () => {
    vi.useFakeTimers();

    useAuthMock.mockReturnValue({
      hasPermission: () => false,
      isLoading: false,
    });

    render(
      <PermissionGuard requiredPermission="user:read">
        <div>protected child</div>
      </PermissionGuard>,
    );

    // Before redirects replaceMock should not be called
    expect(replaceMock).not.toHaveBeenCalled();

    vi.advanceTimersByTime(2000);

    expect(replaceMock).toHaveBeenCalledWith("/");

    // return to real timer
    vi.useRealTimers();
  });
});
