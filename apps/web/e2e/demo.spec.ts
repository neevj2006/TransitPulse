import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("demonstration works without a backend and preserves truthful degraded states", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/");
  await expect(page.getByLabel("Demonstration controls")).toBeVisible();
  await page.getByRole("combobox", { name: "Playback" }).selectOption("0");
  await page
    .getByRole("combobox", { name: "Search routes, stops, or destinations" })
    .fill("Harvard");
  await page.getByRole("link", { name: "Harvard Demonstration stop" }).click();
  await expect(
    page.getByRole("heading", { name: "Upcoming departures" }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Scenario" }).selectOption("outage");
  await expect(page.getByText(/Demo · Scheduled/).first()).toBeVisible();
  await expect(page.getByText("Demo · Live", { exact: true })).toHaveCount(0);
  await page.goto("/reliability");
  await expect(
    page.getByRole("heading", { name: "Data context" }),
  ).toBeVisible();
  await page.getByLabel("Route", { exact: true }).fill("Blue");
  await expect(
    page.getByRole("heading", { name: "No matching reliability evidence" }),
  ).toBeVisible();
  await page.getByLabel("Route", { exact: true }).clear();
  await expect(page.getByText("180", { exact: true })).toBeVisible();
  await page.goto("/transfer-risk");
  await page.getByLabel("Planned arrival", { exact: true }).fill("");
  await expect(
    page.getByRole("button", { name: "Calculate transfer risk" }),
  ).toBeDisabled();
  await page
    .getByLabel("Planned arrival", { exact: true })
    .fill("2026-07-24T10:00");
  await page
    .getByLabel("Planned connecting departure")
    .fill("2026-07-24T10:30");
  await page.getByRole("button", { name: "Calculate transfer risk" }).click();
  await expect(page.getByRole("heading", { name: /Low risk/ })).toBeVisible();
  await page.goto("/operator/feeds");
  await expect(page.getByRole("table")).toBeVisible();
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
  }
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(errors).toEqual([]);
});
