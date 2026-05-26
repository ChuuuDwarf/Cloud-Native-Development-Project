import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: () => "/machine",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { name: "Tester", role: "system_admin" },
    logout: vi.fn(),
    hasPermission: () => true,
  }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    style,
  }: {
    href: string;
    children: React.ReactNode;
    style?: React.CSSProperties;
  }) => (
    <a href={href} style={style}>
      {children}
    </a>
  ),
}));

import Sidebar from "@/components/Sidebar";

// Sidebar uses useQuery (master-data); render inside a QueryClientProvider.
function renderSidebar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <Sidebar />
    </QueryClientProvider>,
  );
}

describe("Sidebar", () => {
  it("renders core navigation groups and links", () => {
    const html = renderSidebar();

    expect(html).toContain("LIMS");
    expect(html).toContain("主管儀表板");
    expect(html).toContain("派工排程");
    expect(html).toContain("機台管理");
    expect(html).toContain("Recipe 管理");
    expect(html).toContain('href="/machine"');
  });

  it("marks the current pathname as active", () => {
    const html = renderSidebar();

    expect(html).toContain("3px solid var(--blue)");
    expect(html).toContain("rgba(56,139,253,0.15)");
  });
});
