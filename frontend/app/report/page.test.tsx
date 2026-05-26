// 報告頁角色權限測試：鎖住「建立報告需 reports:operate（主管/管理者繼承人員權限）」。
// useResourceQuery 被 mock 成 offline=false（回傳 fallback 假資料），否則新增按鈕會因
// 離線而恆為 disabled。權限改由 useAuth().hasPermission 決定（不再有角色切換器），
// 故 mock useAuth。頁面用到 useQueryClient/useQuery，以 QueryClientProvider 包裝渲染。
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useResourceQuery", () => ({
  useResourceQuery: (_key: unknown, _fn: unknown, fallback: unknown) => ({
    data: fallback,
    loading: false,
    offline: false,
    reload: vi.fn(),
  }),
}));

const hasPermissionMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

import ReportPage from "@/../app/report/page";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ReportPage />
    </QueryClientProvider>,
  );
}

const createBtn = () => screen.getByRole("button", { name: /新增報告/ });

describe("報告頁 · 新增報告權限", () => {
  it("有 reports:operate 可新增報告（人員/主管/管理者）", () => {
    hasPermissionMock.mockImplementation((code: string) => code === "reports:operate");
    renderPage();
    expect(createBtn()).toBeEnabled();
  });

  it("無 reports:operate 不可新增報告（廠區使用者）", () => {
    hasPermissionMock.mockReturnValue(false);
    renderPage();
    expect(createBtn()).toBeDisabled();
  });
});
