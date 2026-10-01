import { expect, it } from "vitest";
import { liveArrivalSchema } from "./rider-data";
it("accepts scheduled fallback without inventing realtime freshness", () => {
  const value = liveArrivalSchema.parse({
    trip_id: "trip",
    route_id: "Red",
    agency_prediction: null,
    scheduled_fallback: { gtfs_seconds: 0 },
  });
  expect(value.freshness.state).toBe("UNKNOWN");
  expect(value.agency_prediction).toBeNull();
});
