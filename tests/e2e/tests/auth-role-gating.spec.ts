import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("plant_user sidebar omits admin-only sections, and /account is gated", async ({
  page,
}) => {
  await login(page, "requester@example.com", "Reque1234");

  // Plant user's seed permissions: orders:read, orders:create, samples:read,
  // notifications:read, labs:read, departments:read. samples:read lets them
  // see sample status inside their own order detail page, but the
  // engineer-only workflow nav entries are gated on samples:create, which
  // plant_user does NOT have. So they see only:
  //   委託流程 (orders:read -> 委託單管理)
  // They must NOT see:
  //   執行與機台, 結案與倉儲, 系統, 簽核管理, 帳號管理,
  //   OVERVIEW, 收樣管理, 樣品交接
  await expect(page.getByRole("link", { name: /委託單管理/ })).toBeVisible();

  await expect(page.getByRole("link", { name: /收樣管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /樣品交接/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /執行與機台/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /結案與倉儲/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /系統/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /簽核管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /帳號管理/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /OVERVIEW/ })).toHaveCount(0);

  // Directly navigate to /account. The route may render the page shell, but
  // users:create is still gated, so plant_user must not see the create button.
  await page.goto("/account");

  await expect(page.getByRole("heading", { name: "帳號管理" })).toBeVisible();
  await expect(page.getByRole("button", { name: "+ 建立使用者" })).toHaveCount(0);

  // The users API should fail with 403 or settle into an empty state depending
  // on query timing and UI handling.
  const failure = page.getByText("讀取失敗");
  const empty = page.getByText("沒有符合條件的使用者");

  await expect(failure.or(empty)).toBeVisible();
});