import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test("admin creates a new user via the modal -> row appears in the table", async ({
  page,
}) => {
  await login(page, "admin@example.com", "Admin1234");
  await page.goto("/account");
  await expect(page.getByRole("heading", { name: "帳號管理" })).toBeVisible();

  const email = `e2e-${Date.now()}@example.com`;
  const name = `e2e-${Date.now()}`;

  await page.getByText("+ 建立使用者").click();
  // Modal heading
  await expect(page.getByRole("heading", { name: "建立使用者" })).toBeVisible();

  // Fill the form. Use label-based queries since CSS-var inputs don't have
  // identifying placeholders.
  await page.getByLabel("姓名").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/密碼/).fill("Passw0rd!");

  // Submit and wait for the modal to close.
  await page.getByRole("button", { name: /^建立$/ }).click();
  await expect(page.getByRole("heading", { name: "建立使用者" })).toHaveCount(0, {
    timeout: 10_000,
  });

  // New row visible in the table after the invalidate.
  await expect(page.getByText(email)).toBeVisible({ timeout: 10_000 });
});
