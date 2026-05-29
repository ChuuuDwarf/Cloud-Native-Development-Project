import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// useAuth — swap permissions per test.
const useAuthMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

// userApi.list / create — mock the whole module.
const listMock = vi.fn();
const createMock = vi.fn();
const updateMock = vi.fn();
vi.mock("@/services/user-api", () => ({
  userApi: {
    list: (...args: unknown[]) => listMock(...args),
    create: (...args: unknown[]) => createMock(...args),
    update: (...args: unknown[]) => updateMock(...args),
    getById: vi.fn(),
  },
}));

// masterDataApi.fetch — mock so the create modal selects can populate.
const fetchMock = vi.fn();
vi.mock("@/services/master-data-api", () => ({
  masterDataApi: {
    fetch: (...args: unknown[]) => fetchMock(...args),
  },
}));

// next/navigation — AccountPage is wrapped in PermissionGuard which calls
// useRouter() for the redirect-on-denied path. Mock it so the test renderer
// doesn't crash with "invariant expected app router to be mounted".
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

import AccountPage from "@/../app/account/page";

const seedUsers = [
  {
    id: "u-1",
    email: "admin@example.com",
    name: "Admin",
    departmentId: null,
    labId: null,
    status: "active" as const,
    isActive: true,
    roles: [{ id: "r-1", name: "system_admin" }],
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
  },
  {
    id: "u-2",
    email: "supervisor@example.com",
    name: "Supervisor",
    departmentId: null,
    labId: "lab-1",
    status: "active" as const,
    isActive: true,
    roles: [{ id: "r-2", name: "lab_supervisor" }],
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
  },
  {
    id: "u-3",
    email: "engineer@example.com",
    name: "Engineer",
    departmentId: null,
    labId: "lab-1",
    status: "active" as const,
    isActive: true,
    roles: [{ id: "r-3", name: "lab_engineer" }],
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
  },
  {
    id: "u-4",
    email: "requester@example.com",
    name: "Requester",
    departmentId: "dept-1",
    labId: null,
    status: "active" as const,
    isActive: true,
    roles: [{ id: "r-4", name: "plant_user" }],
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
  },
];

const seedMasterData = {
  roles: [
    { id: "r-1", name: "system_admin", description: "", permissions: ["*"] },
    { id: "r-2", name: "lab_supervisor", description: "", permissions: [] },
  ],
  permissions: [],
  labs: [{ id: "lab-1", code: "L01", name: "Lab 1", capacity: 10 }],
  departments: [{ id: "dept-1", code: "D01", name: "Dept 1" }],
  storageLocations: [],
  experimentItems: [],
  orderStatuses: [],
  wipStatuses: [],
  machineStatuses: [],
  reportStatuses: [],
  issueStatuses: [],
  issueTypes: [],
  notificationStatuses: [],
  userStatuses: [],
  severities: [],
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AccountPage />
    </QueryClientProvider>
  );
}

function makeAuth(perms: string[]) {
  const set = new Set(perms);
  return {
    user: {
      id: "u-admin",
      name: "Admin",
      email: "admin@example.com",
      role: "system_admin",
      permissions: perms,
      labId: null,
      departmentId: null,
    },
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    hasPermission: (c: string) => set.has("*") || set.has(c),
  };
}

describe("AccountPage", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    listMock.mockReset();
    createMock.mockReset();
    updateMock.mockReset();
    fetchMock.mockReset();
    listMock.mockResolvedValue({
      items: seedUsers,
      page: 1,
      pageSize: 100,
      total: seedUsers.length,
    });
    fetchMock.mockResolvedValue(seedMasterData);
  });

  it("renders 4 user rows with active status pills when admin", async () => {
    useAuthMock.mockReturnValue(makeAuth(["*"]));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Admin")).toBeInTheDocument();
    });
    expect(screen.getByText("Supervisor")).toBeInTheDocument();
    expect(screen.getByText("Engineer")).toBeInTheDocument();
    expect(screen.getByText("Requester")).toBeInTheDocument();

    // 4 active pills
    const activePills = screen.getAllByText("啟用");
    // Note: "啟用" appears both in StatusPill (label) and in the row's
    // toggle button when isActive=false. Since all 4 seed users are active,
    // they show 啟用 only in the pill, and the toggle button shows 停用.
    expect(activePills.length).toBe(4);
    // 建立使用者 is visible
    expect(screen.getByText("+ 建立使用者")).toBeInTheDocument();
  });

  it("hides + 建立使用者 when non-admin lacks users:create", async () => {
    useAuthMock.mockReturnValue(makeAuth(["users:read"]));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Admin")).toBeInTheDocument();
    });
    expect(screen.queryByText("+ 建立使用者")).not.toBeInTheDocument();
  });

  it("clicking + 建立使用者 opens the modal with roles/dept/lab selects populated", async () => {
    useAuthMock.mockReturnValue(makeAuth(["*"]));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("+ 建立使用者")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("+ 建立使用者"));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    expect(screen.getByText("建立使用者")).toBeInTheDocument();

    // Wait for masterData query to resolve, then assert select options exist.
    // Use role=option since <option> text isn't always discoverable via getByText in jsdom.
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "system_admin" })).toBeInTheDocument();
    });
    expect(screen.getByRole("option", { name: "lab_supervisor" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "D01 · Dept 1" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "L01 · Lab 1" })).toBeInTheDocument();
  });
});
