import { expect, test } from "@playwright/test";

test("scheduled network proof is keyboard-accessible", async ({ page }) => {
  await page.goto("/schedule");
  await expect(page.getByRole("heading", { name: "Find MBTA routes and stops" })).toBeVisible();
  await page.getByLabel("Search routes or stops").focus();
  await expect(page.getByRole("link", { name: "View schedule" }).first()).toBeVisible();
});
