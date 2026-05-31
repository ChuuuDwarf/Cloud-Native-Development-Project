import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

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

vi.mock("@/services/master-data-api", () => ({
  masterDataApi: {
    fetch: vi.fn().mockResolvedValue({
      labs: [
        {
          id: "lab-a",
          code: "LAB-A",
          name: "材料分析實驗室",
        },
        {
          id: "lab-b",
          code: "LAB-B",
          name: "電性測試實驗室",
        },
      ],
      departments: [],
      experiments: [],
    }),
  },
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

function renderSidebar() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <Sidebar />
    </QueryClientProvider>
  );
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
      })
    );

    renderSidebar();

    expect(screen.getByText("OVERVIEW")).toBeInTheDocument();
    expect(screen.getByText("委託流程")).toBeInTheDocument();
    expect(screen.getByText("執行與機台")).toBeInTheDocument();
    expect(screen.getByText("結案與通知")).toBeInTheDocument();
    expect(screen.getByText("系統")).toBeInTheDocument();

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
        labId: "lab-a",
        departmentId: null,
      })
    );

    renderSidebar();

    expect(screen.getByText("OVERVIEW")).toBeInTheDocument();
    expect(screen.getByText("委託流程")).toBeInTheDocument();
    expect(screen.getByText("執行與機台")).toBeInTheDocument();
    expect(screen.getByText("結案與通知")).toBeInTheDocument();

    expect(screen.queryByText("系統")).not.toBeInTheDocument();
    expect(screen.queryByText("帳號管理")).not.toBeInTheDocument();

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
        labId: "lab-a",
        departmentId: null,
      })
    );

    renderSidebar();

    expect(screen.getByText("派工排程")).toBeInTheDocument();
    expect(screen.getByText("機台管理")).toBeInTheDocument();
    expect(screen.getByText("Recipe 管理")).toBeInTheDocument();

    expect(screen.queryByText("簽核管理")).not.toBeInTheDocument();
    expect(screen.queryByText("帳號管理")).not.toBeInTheDocument();
    expect(screen.queryByText("系統")).not.toBeInTheDocument();
  });

  it("plant_user sees allowed 委託流程 items only", () => {
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
      })
    );

    renderSidebar();

    expect(screen.getByText("委託單管理")).toBeInTheDocument();
    expect(screen.getByText("委託流程")).toBeInTheDocument();

    expect(screen.queryByText("簽核管理")).not.toBeInTheDocument();
    expect(screen.getByText("樣品追蹤")).toBeInTheDocument();
    expect(screen.queryByText("分貨 / WIP")).not.toBeInTheDocument();

    expect(screen.queryByText("執行與機台")).not.toBeInTheDocument();
    expect(screen.queryByText("系統")).not.toBeInTheDocument();
    expect(screen.queryByText("OVERVIEW")).not.toBeInTheDocument();

    // 結案與通知 section is hidden for plant_user: no item in it is allowed
    // for them (notifications is engineer / supervisor / admin only).
    expect(screen.queryByText("結案與通知")).not.toBeInTheDocument();
    expect(screen.queryByText("通知中心")).not.toBeInTheDocument();
    expect(screen.queryByText("倉儲取件")).not.toBeInTheDocument();
    expect(screen.queryByText("異常與告警")).not.toBeInTheDocument();
  });

  it("footer shows user.name + resolved role label", () => {
    useAuthMock.mockReturnValue(
      makeAuth({
        id: "u-admin",
        name: "Admin",
        email: "admin@example.com",
        role: "system_admin",
        permissions: ["*"],
        labId: null,
        departmentId: null,
      })
    );

    renderSidebar();

    expect(screen.getByText("Admin")).toBeInTheDocument();
    expect(screen.getByText("系統管理者")).toBeInTheDocument();
  });

  it("footer shows lab code + role label when user has labId", async () => {
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
        labId: "lab-a",
        departmentId: null,
      })
    );

    renderSidebar();

    expect(screen.getByText("Engineer")).toBeInTheDocument();
    expect(await screen.findByText("LAB-A / 實驗室人員")).toBeInTheDocument();
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
        logout
      )
    );

    renderSidebar();

    const btn = screen.getByRole("button", { name: "登出" });
    fireEvent.click(btn);

    await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/"));
  });
});
