import { expect, type Page } from "@playwright/test";

/**
 * Log in by typing credentials into the LoginForm rendered on the homepage
 * when there's no auth cookie. Asserts that the sidebar logo "LIMS" is
 * visible afterwards, which is the signal that AuthGate has switched from
 * the login view to the authed shell.
 */
export async function login(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/");
  // The login form is rendered when not authenticated.
  await page.getByPlaceholder("admin@example.com").fill(email);
  // 密碼 input — first password-type input in the form.
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /登入/ }).click();

  // After successful login, AuthGate swaps to the Sidebar+main shell. The
  // sidebar logo span "LIMS" is a stable signal that the swap happened.
  await expect(page.getByText("LIMS", { exact: true })).toBeVisible({
    timeout: 10_000,
  });
}
