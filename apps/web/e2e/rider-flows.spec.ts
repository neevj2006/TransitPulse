import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("rider pages preserve truthful fallback states and keyboard paths", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/stops/Harvard");
  await expect(page.getByText("Live predictions unavailable")).toBeVisible();
  await expect(page.getByText("No upcoming service")).toBeVisible();
  await page.goto("/routes/Red");
  await expect(
    page.getByRole("heading", { name: "Red", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Scheduled service")).toBeVisible();
  await page.goto("/map");
  await expect(page.getByText("Last-known locations expire")).toBeVisible();
  await page.goto("/alerts");
  await page.getByLabel("Filter agency alerts").fill("Red");
  await expect(page.getByText("No active alerts")).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(errors).toEqual([]);
});
