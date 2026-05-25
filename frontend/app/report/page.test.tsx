// 報告頁角色權限測試：鎖住「主管繼承人員權限，可建立報告」這條規則。
// useResourceQuery 被 mock 成 offline=false（回傳 fallback 假資料），否則新增按鈕
// 會因離線而恆為 disabled，測不到角色邏輯。頁面用到 useQueryClient，故以
// QueryClientProvider 包裝渲染（對齊 app/__tests__/AccountPage.test.tsx 的寫法）。
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useResourceQuery", () => ({
  useResourceQuery: (_key: unknown, _fn: unknown, fallback: unknown) => ({
    data: fallback,
    loading: false,
    offline: false,
    reload: vi.fn(),
  }),
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
const roleSelect = () => screen.getByRole("combobox");

describe("報告頁 · 新增報告權限", () => {
  it("實驗室人員可新增報告", () => {
    renderPage();
    expect(createBtn()).toBeEnabled();
  });

  it("實驗室主管可新增報告（繼承人員權限）", () => {
    renderPage();
    fireEvent.change(roleSelect(), { target: { value: "實驗室主管" } });
    expect(createBtn()).toBeEnabled();
  });

  it("廠區使用者不可新增報告", () => {
    renderPage();
    fireEvent.change(roleSelect(), { target: { value: "廠區使用者" } });
    expect(createBtn()).toBeDisabled();
  });

  it("系統管理者不可新增報告", () => {
    renderPage();
    fireEvent.change(roleSelect(), { target: { value: "系統管理者" } });
    expect(createBtn()).toBeDisabled();
  });
});
