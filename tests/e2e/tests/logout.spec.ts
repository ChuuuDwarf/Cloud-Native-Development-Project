import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test("admin logout clears the auth cookie and returns to LoginForm", async ({
  page,
  context,
}) => {
  await login(page, "admin@example.com", "Admin1234");

  // Before logout: the access_token cookie is set by the backend.
  const before = await context.cookies();
  expect(before.some((c) => c.name === "access_token")).toBe(true);

  await page.getByRole("button", { name: "登出" }).click();

  // LoginForm reappears (placeholder is a stable signal).
  await expect(page.getByPlaceholder("admin@example.com")).toBeVisible({
    timeout: 10_000,
  });

  // Cookie cleared.
  const after = await context.cookies();
  expect(after.some((c) => c.name === "access_token")).toBe(false);
});
