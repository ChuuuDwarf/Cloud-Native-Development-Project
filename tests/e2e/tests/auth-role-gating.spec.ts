import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("plant_user sidebar omits admin-only sections, and /account is gated", async ({
  page,
}) => {
  await login(page, "requester@example.com", "Reque1234");

  // Plant user has orders and sample read permissions, so they can see
  // order management and sample receiving/status navigation.
  await expect(page.getByRole("link", { name: /委託單管理/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /收樣管理/ })).toBeVisible();

  // Plant user must not see engineer/admin-only navigation entries.
  await expect(page.getByRole("link", { name: /樣品交接/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /執行與機台/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /結案與倉儲/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /系統/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /簽核管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /帳號管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /OVERVIEW/ })).toHaveCount(0);

  await page.goto("/account");

  await expect(page.getByRole("heading", { name: "帳號管理" })).toBeVisible();
  await expect(page.getByRole("button", { name: "+ 建立使用者" })).toHaveCount(0);

  const failure = page.getByText("讀取失敗");
  const empty = page.getByText("沒有符合條件的使用者");

  await expect(failure.or(empty)).toBeVisible();
});