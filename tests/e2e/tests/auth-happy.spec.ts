import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test("admin login -> dashboard -> system section visible -> /account lists seed users", async ({
  page,
}) => {
  await login(page, "admin@example.com", "Admin1234");

  // 系統 section is admin-only (needs users:read or system_settings:read)
  await expect(page.getByText("系統", { exact: true })).toBeVisible();
  await expect(page.getByText("帳號管理", { exact: true })).toBeVisible();

  // Navigate to /account
  await page.getByText("帳號管理", { exact: true }).click();
  await expect(page).toHaveURL(/\/account$/);

  // Page header
  await expect(page.getByRole("heading", { name: "帳號管理" })).toBeVisible();

  // Table should include the seed admin row
  await expect(page.getByText("admin@example.com")).toBeVisible();

  // At least 4 user rows (admin/supervisor/engineer/requester seed accounts)
  const rows = page.locator("table tbody tr");
  await expect(rows).toHaveCount(await rows.count());
  expect(await rows.count()).toBeGreaterThanOrEqual(4);
});
