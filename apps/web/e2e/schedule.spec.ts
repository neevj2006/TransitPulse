import { expect, test } from "@playwright/test";

test("scheduled network proof is keyboard-accessible", async ({ page }) => {
  await page.goto("/schedule");
  await expect(
    page.getByRole("heading", { name: "Find MBTA routes and stops" }),
  ).toBeVisible();
  await page.getByLabel("Search routes, stops, or destinations").focus();
  await expect(
    page.getByRole("link", { name: "Red route and stops" }),
  ).toBeVisible();
});
