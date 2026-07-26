import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

async function mockRiderApi(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    class TestEventSource extends EventTarget {
      close() {}
      addEventListener(
        type: string,
        listener: EventListenerOrEventListenerObject | null,
      ) {
        super.addEventListener(type, listener);
      }
    }
    // @ts-expect-error browser test replacement
    window.EventSource = TestEventSource;
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const data = path.endsWith("/search")
      ? [
          {
            kind: "route",
            id: "Red",
            label: "Red",
            detail: "Red Line",
            route_color: "#da291c",
          },
          { kind: "stop", id: "Harvard", label: "Harvard", detail: null },
        ]
      : path.endsWith("/live/health")
        ? [{ state: "HEALTHY" }]
        : path.endsWith("/live/vehicles")
          ? [
              {
                vehicle_id: "train-1",
                route_id: "Red",
                trip_id: "trip-1",
                latitude: 42.36,
                longitude: -71.06,
                freshness: { state: "HEALTHY" },
              },
            ]
          : path.endsWith("/vehicles")
            ? [
                {
                  vehicle_id: "train-1",
                  route_id: "Red",
                  trip_id: "trip-1",
                  latitude: 42.36,
                  longitude: -71.06,
                  freshness: { state: "HEALTHY" },
                },
              ]
            : path.endsWith("/routes/Red/stops")
              ? {
                  directions: [0, 1],
                  headsign: "Alewife",
                  stops: [
                    {
                      stop_id: "Harvard",
                      name: "Harvard",
                      sequence: 1,
                      scheduled_seconds: 36000,
                    },
                  ],
                }
              : path.endsWith("/routes/Red/vehicles")
                ? [
                    {
                      vehicle_id: "train-1",
                      route_id: "Red",
                      trip_id: "trip-1",
                      latitude: 42.36,
                      longitude: -71.06,
                      freshness: { state: "HEALTHY" },
                    },
                  ]
                : path.endsWith("/live/stops/Harvard/arrivals")
                  ? []
                  : path.endsWith("/stops/Harvard/arrivals")
                    ? [
                        {
                          trip_id: "trip-1",
                          route_id: "Red",
                          headsign: "Alewife",
                          scheduled: {
                            service_date: "2026-07-26",
                            gtfs_seconds: 36000,
                          },
                        },
                      ]
                    : path.endsWith("/live/alerts")
                      ? [
                          {
                            alert_id: "alert-1",
                            header: "Shuttle buses",
                            effect: "Detour",
                            route_ids: ["Red"],
                            stop_ids: ["Harvard"],
                            source_timestamp: "2026-07-26T10:00:00Z",
                            freshness: { state: "HEALTHY" },
                          },
                        ]
                      : [];
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ schema_version: "1.0.0", data, meta: {} }),
    });
  });
}

test("riders can search, inspect live vehicles, and filter agency alerts", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await mockRiderApi(page);
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/");
  const search = page.getByRole("combobox", {
    name: "Search routes, stops, or destinations",
  });
  await search.fill("Red");
  await expect(page.getByRole("link", { name: /Red Red Line/ })).toBeVisible();
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Red", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Harvard").last()).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Red.*Trip trip-1/ }),
  ).toBeVisible();
  await page.goto("/map");
  await expect(
    page.getByRole("button", { name: /Red.*Trip trip-1/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Red.*Trip trip-1/ }).click();
  await expect(page.getByLabel("Vehicle detail")).toBeVisible();
  await page.goto("/alerts");
  await expect(page.getByText("Shuttle buses")).toBeVisible();
  await page.getByLabel("Filter agency alerts").fill("Orange");
  await expect(
    page.getByRole("heading", { name: "No active alerts" }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(errors).toEqual([]);
});
