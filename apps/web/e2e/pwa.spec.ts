import { expect, test } from "@playwright/test";

test("the app exposes install metadata and keeps realtime endpoints out of the offline cache", async ({
  page,
}) => {
  await page.goto("/");
  const manifest = await page.evaluate(async () => {
    const response = await fetch("/manifest.webmanifest");
    return response.json();
  });
  expect(manifest.name).toBe("TransitPulse");
  expect(manifest.display).toBe("standalone");
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
    "href",
    "/manifest.webmanifest",
  );

  const serviceWorker = await page.request.get("/sw.js");
  expect(serviceWorker.ok()).toBeTruthy();
  expect(await serviceWorker.text()).toContain(
    'url.pathname.startsWith("/api/")',
  );
});
