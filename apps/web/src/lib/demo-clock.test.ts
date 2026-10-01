import { expect, it, vi } from "vitest";
import {
  configureDemo,
  demoQuery,
  demoSeconds,
  demoSnapshot,
} from "./demo-clock";
it("pauses, accelerates, and restarts without losing the selected scenario", () => {
  vi.useFakeTimers();
  configureDemo(0, "outage", true);
  vi.advanceTimersByTime(10000);
  expect(demoSeconds()).toBe(0);
  expect(demoSnapshot()).toEqual({ speed: 0, scenario: "outage" });
  configureDemo(10, "stale");
  vi.advanceTimersByTime(6000);
  expect(demoQuery().get("demo_seconds")).toBe("60");
  configureDemo(1, "healthy", true);
  expect(demoSeconds()).toBe(0);
  vi.useRealTimers();
});
