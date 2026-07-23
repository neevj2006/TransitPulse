import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const viewports = [
  { name: "compact", width: 320, height: 720 },
  { name: "medium", width: 768, height: 900 },
  { name: "large", width: 1440, height: 900 },
];

test("health page works across themes and responsive widths", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/health");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "The web foundation is ready.",
    );
    await expect(page.getByText("Unavailable")).toBeVisible();
    const horizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(
      horizontalOverflow,
      `${viewport.name} viewport overflowed`,
    ).toBeFalsy();
  }

  const theme = page.getByRole("combobox", { name: "Color theme" });
  await theme.selectOption("dark");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await theme.selectOption("light");
  await expect(page.locator("html")).toHaveClass(/light/);

  await page.keyboard.press("Home");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to main content" }),
  ).toBeFocused();

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("health API exposes validated version information", async ({
  request,
}) => {
  const response = await request.get("/api/health");
  expect(response.ok()).toBeTruthy();
  await expect(response.json()).resolves.toMatchObject({
    service: "transitpulse-web",
    status: "ok",
  });
});
