import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock Next.js navigation hooks used by Sidebar.
const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}));

// Mock useAuth — different tests will swap the return value.
const useAuthMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

import Sidebar from "@/components/Sidebar";

type FakeUser = {
  id: string;
  name: string;
  email: string;
  role: string;
  permissions: string[];
  labId: string | null;
  departmentId: string | null;
};

function makeAuth(user: FakeUser, logout = vi.fn()) {
  const perms = new Set(user.permissions);
  return {
    user,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout,
    refresh: vi.fn(),
    hasPermission: (code: string) => perms.has("*") || perms.has(code),
  };
}

describe("Sidebar", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    replaceMock.mockReset();
  });

  it("system_admin with permissions:['*'] sees every section", () => {
    useAuthMock.mockReturnValue(
      makeAuth({
        id: "u-admin",
        name: "Admin",
        email: "admin@example.com",
        role: "system_admin",
        permissions: ["*"],
        labId: null,
        departmentId: null,
      }),
    );

    render(<Sidebar />);

    expect(screen.getByText("OVERVIEW")).toBeInTheDocument();
    expect(screen.getByText("委託流程")).toBeInTheDocument();
    expect(screen.getByText("執行與機台")).toBeInTheDocument();
    expect(screen.getByText("結案與倉儲")).toBeInTheDocument();
    expect(screen.getByText("系統")).toBeInTheDocument();
    // Spot-check items
    expect(screen.getByText("帳號管理")).toBeInTheDocument();
    expect(screen.getByText("系統設定")).toBeInTheDocument();
    expect(screen.getByText("簽核管理")).toBeInTheDocument();
  });

  it("lab_supervisor sees workflow + execution + closing but not the 系統 section", () => {
    useAuthMock.mockReturnValue(
      makeAuth({
        id: "u-sup",
        name: "Supervisor",
        email: "supervisor@example.com",
        role: "lab_supervisor",
        permissions: [
          "dashboard:read",
          "orders:read",
          "orders:approve",
          "samples:read",
          "wips:read",
          "machines:read",
          "machines:manage",
          "recipes:read",
          "dispatches:read",
          "storage_locations:read",
          "issues:read",
        ],
        labId: "lab-1",
        departmentId: null,
      }),
    );

    render(<Sidebar />);

    expect(screen.getByText("OVERVIEW")).toBeInTheDocument();
    expect(screen.getByText("委託流程")).toBeInTheDocument();
    expect(screen.getByText("執行與機台")).toBeInTheDocument();
    expect(screen.getByText("結案與倉儲")).toBeInTheDocument();
    // No 系統 section because no users:read / system_settings:read
    expect(screen.queryByText("系統")).not.toBeInTheDocument();
    expect(screen.queryByText("帳號管理")).not.toBeInTheDocument();
    // Has the approve item
    expect(screen.getByText("簽核管理")).toBeInTheDocument();
  });

  it("lab_engineer sees execution items but not 簽核管理 or 帳號管理", () => {
    useAuthMock.mockReturnValue(
      makeAuth({
        id: "u-eng",
        name: "Engineer",
        email: "engineer@example.com",
        role: "lab_engineer",
        permissions: [
          "samples:read",
          "wips:read",
          "machines:read",
          "recipes:read",
          "dispatches:read",
          "storage_locations:read",
          "issues:read",
        ],
        labId: "lab-1",
        departmentId: null,
      }),
    );

    render(<Sidebar />);

    // Has execution items
    expect(screen.getByText("派工排程")).toBeInTheDocument();
    expect(screen.getByText("機台管理")).toBeInTheDocument();
    expect(screen.getByText("Recipe 管理")).toBeInTheDocument();
    // Should NOT have approve or account
    expect(screen.queryByText("簽核管理")).not.toBeInTheDocument();
    expect(screen.queryByText("帳號管理")).not.toBeInTheDocument();
    expect(screen.queryByText("系統")).not.toBeInTheDocument();
  });

  it("plant_user sees ONLY 委託單管理 under 委託流程", () => {
    useAuthMock.mockReturnValue(
      makeAuth({
        id: "u-plant",
        name: "Requester",
        email: "requester@example.com",
        role: "plant_user",
        permissions: [
          "orders:read",
          "orders:create",
          "notifications:read",
          "labs:read",
          "departments:read",
        ],
        labId: null,
        departmentId: "dept-1",
      }),
    );

    render(<Sidebar />);

    // 委託流程 section visible with only 委託單管理 inside
    expect(screen.getByText("委託單管理")).toBeInTheDocument();
    expect(screen.getByText("委託流程")).toBeInTheDocument();
    // No other items in workflow section
    expect(screen.queryByText("簽核管理")).not.toBeInTheDocument();
    expect(screen.queryByText("收樣管理")).not.toBeInTheDocument();
    expect(screen.queryByText("分貨 / WIP")).not.toBeInTheDocument();
    // No other sections (no samples:read so no 樣品交接 in 執行與機台)
    expect(screen.queryByText("執行與機台")).not.toBeInTheDocument();
    expect(screen.queryByText("結案與倉儲")).not.toBeInTheDocument();
    expect(screen.queryByText("系統")).not.toBeInTheDocument();
    expect(screen.queryByText("OVERVIEW")).not.toBeInTheDocument();
  });

  it("footer shows user.name + user.role", () => {
    useAuthMock.mockReturnValue(
      makeAuth({
        id: "u-admin",
        name: "Admin",
        email: "admin@example.com",
        role: "system_admin",
        permissions: ["*"],
        labId: null,
        departmentId: null,
      }),
    );

    render(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    expect(screen.getByText("system_admin")).toBeInTheDocument();
  });

  it("clicking 登出 calls logout()", async () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    useAuthMock.mockReturnValue(
      makeAuth(
        {
          id: "u-admin",
          name: "Admin",
          email: "admin@example.com",
          role: "system_admin",
          permissions: ["*"],
          labId: null,
          departmentId: null,
        },
        logout,
      ),
    );

    render(<Sidebar />);
    const btn = screen.getByRole("button", { name: "登出" });
    fireEvent.click(btn);

    await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/"));
  });
});
