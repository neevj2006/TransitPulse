import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

test("primary demonstration screens remain usable across themes", async ({
  page,
}) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const output = path.resolve("../../docs/images");
  if (process.env.CAPTURE_PORTFOLIO) await mkdir(output, { recursive: true });
  for (const theme of ["light", "dark"]) {
    for (const [name, route] of [
      ["home", "/"],
      ["arrivals", "/stops/Harvard"],
      ["map", "/map"],
      ["reliability", "/reliability"],
      ["transfer", "/transfer-risk"],
      ["operator", "/operator/feeds"],
    ]) {
      await page.goto(route);
      await page
        .getByRole("combobox", { name: "Color theme" })
        .selectOption(theme);
      await page.getByRole("combobox", { name: "Playback" }).selectOption("0");
      await expect(page.locator("main h1")).toBeVisible();
      if (route === "/")
        await expect(
          page.getByRole("heading", { name: "Network status" }),
        ).toBeVisible();
      if (route === "/transfer-risk") {
        await page
          .getByLabel("Planned arrival", { exact: true })
          .fill("2026-07-24T10:00");
        await page
          .getByLabel("Planned connecting departure")
          .fill("2026-07-24T10:10");
        await page
          .getByRole("button", { name: "Calculate transfer risk" })
          .click();
        await expect(
          page.getByRole("heading", { name: /risk ·/ }),
        ).toBeVisible();
      }
      if (route === "/map") {
        await expect(
          page.getByRole("heading", { name: "Vehicle list" }),
        ).toBeVisible();
        await expect(
          page.getByRole("heading", { name: "MBTA network map" }),
        ).toBeVisible();
      }
      if (route === "/reliability")
        await expect(
          page.getByRole("heading", { name: "Median delay by observed hour" }),
        ).toBeVisible();
      if (route === "/operator/feeds")
        await expect(page.getByRole("table")).toBeVisible();
      if (route === "/stops/Harvard")
        await expect(
          page.getByRole("heading", { name: "Upcoming departures" }),
        ).toBeVisible();
      if (process.env.CAPTURE_PORTFOLIO) {
        await page.evaluate(() => window.scrollTo(0, 0));
        // Let canvas tiles and chart animations settle for exported images.
        await page.waitForTimeout(2000);
        await page.screenshot({
          path: path.join(output, `${name}-${theme}.png`),
          fullPage: true,
          animations: "disabled",
          style: "nextjs-portal { display: none; }",
        });
      }
    }
  }
  await page.goto("/stops/Harvard");
  await expect(page.getByText("Demo · Live", { exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Scenario" }).selectOption("outage");
  await expect(page.getByText(/Demo · Scheduled/).first()).toBeVisible();
  await expect(page.getByText("Demo · Live", { exact: true })).toHaveCount(0);
  if (process.env.CAPTURE_PORTFOLIO)
    await page.screenshot({
      path: path.join(output, "scheduled-fallback.png"),
      fullPage: true,
      style: "nextjs-portal { display: none; }",
    });
  expect(errors).toEqual([]);
});
