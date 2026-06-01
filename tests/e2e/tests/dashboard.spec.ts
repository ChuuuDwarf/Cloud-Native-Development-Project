import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * Phase F smoke tests for the redesigned supervisor dashboard.
 *
 * Covers:
 * - Unauthenticated visitors see the LoginForm (no dashboard widgets).
 * - general_supervisor (大主管, cross-lab) sees the cross-lab leaderboard
 *   variant of the bottom-right slot.
 * - lab_supervisor (per-lab) sees the 24h throughput chart variant in the
 *   same slot.
 * - The "完工" KPI tile drills to /execution.
 *
 * Seed accounts come from `backend/scripts/seed_dev.py`:
 *   director@example.com   / Direc1234 (general_supervisor, cross-lab)
 *   supervisor@example.com / Super1234 (lab_supervisor,    LAB-A)
 *
 * Note: this project's frontend does NOT redirect unauthenticated visitors
 * to a `/login` route — AuthGate swaps in the <LoginForm /> in-place at the
 * current pathname. So the unauthenticated check asserts the form is
 * visible at "/" rather than a URL change.
 */

const DASHBOARD_HEADING = "主管儀表板";
const KPI_LABELS = ["新單", "完工", "回傳", "待簽", "告警"] as const;

test.describe("Supervisor dashboard", () => {
  test("unauthenticated visitor sees the LoginForm, not dashboard widgets", async ({
    page,
  }) => {
    await page.goto("/");

    // LoginForm visible (placeholder for the email input is a stable signal).
    await expect(page.getByPlaceholder("admin@example.com")).toBeVisible({
      timeout: 10_000,
    });

    // Dashboard widgets must not render for an unauthenticated visitor.
    await expect(page.getByTestId("kpi-bar")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: DASHBOARD_HEADING })).toHaveCount(0);
  });

  test("general_supervisor lands on /, sees cross-lab dashboard with leaderboard", async ({
    page,
  }) => {
    await login(page, "director@example.com", "Direc1234");

    // After login, AuthGate lands the general_supervisor on the dashboard at "/".
    await expect(page).toHaveURL(/\/$/);

    // Header.
    await expect(page.getByRole("heading", { name: DASHBOARD_HEADING })).toBeVisible({
      timeout: 10_000,
    });

    // KPI bar + 5 labels.
    const kpi = page.getByTestId("kpi-bar");
    await expect(kpi).toBeVisible();
    for (const label of KPI_LABELS) {
      await expect(kpi.getByText(label, { exact: true })).toBeVisible();
    }

    // Mid widgets.
    await expect(page.getByTestId("machine-heatmap")).toBeVisible();
    await expect(page.getByTestId("wip-pipeline")).toBeVisible();

    // Bottom-right slot: cross-lab leaderboard for general_supervisor.
    await expect(page.getByTestId("lab-leaderboard")).toBeVisible();
    await expect(page.getByTestId("throughput-chart")).toHaveCount(0);
  });

  test("lab_supervisor lands on /, sees per-lab dashboard with throughput chart", async ({
    page,
  }) => {
    await login(page, "supervisor@example.com", "Super1234");

    await expect(page).toHaveURL(/\/$/);

    await expect(page.getByRole("heading", { name: DASHBOARD_HEADING })).toBeVisible({
      timeout: 10_000,
    });

    // Top widgets identical to the cross-lab view.
    const kpi = page.getByTestId("kpi-bar");
    await expect(kpi).toBeVisible();
    for (const label of KPI_LABELS) {
      await expect(kpi.getByText(label, { exact: true })).toBeVisible();
    }
    await expect(page.getByTestId("machine-heatmap")).toBeVisible();
    await expect(page.getByTestId("wip-pipeline")).toBeVisible();

    // Bottom-right slot: 24h throughput chart for lab_supervisor.
    await expect(page.getByTestId("throughput-chart")).toBeVisible();
    await expect(page.getByTestId("lab-leaderboard")).toHaveCount(0);
  });

  test('clicking the "完工" KPI tile drills to /execution', async ({
    page,
  }) => {
    await login(page, "supervisor@example.com", "Super1234");

    const kpi = page.getByTestId("kpi-bar");
    await expect(kpi).toBeVisible();

    // The KPI tile is a <button>; the "完工" text label is rendered inside it.
    // Click the label and let the parent button receive the event.
    await kpi.getByText("完工", { exact: true }).click();

    await expect(page).toHaveURL(/\/execution$/, {
      timeout: 10_000,
    });
  });
});
