import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("plant_user sidebar omits admin-only sections, and /account is gated", async ({
  page,
}) => {
  await login(page, "requester@example.com", "Reque1234");

  await expect(page.getByRole("link", { name: /委託單管理/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /收樣管理/ })).toBeVisible();

  await expect(page.getByRole("link", { name: /樣品交接/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /執行與機台/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /結案與倉儲/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /系統/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /簽核管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /帳號管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /OVERVIEW/ })).toHaveCount(0);

  await page.goto("/account");

  await expect(page.getByRole("heading", { name: "帳號管理" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "+ 建立使用者" })).toHaveCount(0);

  await expect(
    page.getByText(/403|Forbidden|無權限|沒有權限|未授權|登入/),
  ).toBeVisible();
});