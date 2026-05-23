import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test("plant_user sidebar omits admin-only sections, and /account is gated", async ({
  page,
}) => {
  await login(page, "requester@example.com", "Reque1234");

  // Plant user's seed permissions: orders:read, orders:create, samples:read,
  // notifications:read, labs:read, departments:read. samples:read lets them
  // see sample status inside their own order detail page, but the
  // engineer-only workflow nav entries (收樣管理 / 樣品交接) are gated on
  // samples:create, which plant_user does NOT have. So they see only:
  //   委託流程 (orders:read -> 委託單管理)
  // They must NOT see:
  //   執行與機台 (no member item), 結案與倉儲, 系統, 簽核管理, 帳號管理,
  //   OVERVIEW, 收樣管理, 樣品交接
  await expect(page.getByText("委託單管理", { exact: true })).toBeVisible();

  await expect(page.getByText("收樣管理", { exact: true })).toHaveCount(0);
  await expect(page.getByText("樣品交接", { exact: true })).toHaveCount(0);
  await expect(page.getByText("執行與機台", { exact: true })).toHaveCount(0);
  await expect(page.getByText("結案與倉儲", { exact: true })).toHaveCount(0);
  await expect(page.getByText("系統", { exact: true })).toHaveCount(0);
  await expect(page.getByText("簽核管理", { exact: true })).toHaveCount(0);
  await expect(page.getByText("帳號管理", { exact: true })).toHaveCount(0);
  await expect(page.getByText("OVERVIEW", { exact: true })).toHaveCount(0);

  // Directly navigate to /account — the page renders but the users API
  // returns 403, so the row body should show the read-fail message (or
  // remain empty depending on how the query settles). Either way the
  // heading still renders.
  await page.goto("/account");
  await expect(page.getByRole("heading", { name: "帳號管理" })).toBeVisible();
  // The "+ 建立使用者" button is gated on users:create which plant_user lacks.
  await expect(page.getByText("+ 建立使用者")).toHaveCount(0);
  // Either an empty table or the read-failure message.
  const failure = page.getByText("讀取失敗");
  const empty = page.getByText("沒有符合條件的使用者");
  // Wait for either to appear (within the default 5s).
  await expect(failure.or(empty)).toBeVisible();
});
