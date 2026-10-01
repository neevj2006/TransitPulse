import { describe, expect, it } from "vitest";
import { demoResponse } from "./demo";
const response = (path: string) =>
  demoResponse(new URL(`http://demo/api/v1/${path}`));
describe("deterministic demonstration", () => {
  it("repeats the same playback instant and removes expired vehicles", () => {
    expect(response("live/vehicles?demo_seconds=60")).toEqual(
      response("live/vehicles?demo_seconds=60"),
    );
    expect(response("live/vehicles?demo_seconds=301").body).toMatchObject({
      data: [],
      meta: { mode: "demonstration", synthetic: true },
    });
  });
  it("keeps schedules during an outage and marks stale evidence", () => {
    expect(
      response("live/stops/Harvard/arrivals?demo_scenario=outage").body,
    ).toMatchObject({ data: [] });
    expect(
      response("stops/Harvard/arrivals?demo_scenario=outage").body,
    ).toMatchObject({ data: [{ trip_id: "demo-trip-0" }, {}, {}] });
    expect(response("live/vehicles?demo_scenario=stale").body).toMatchObject({
      data: [{ freshness: { state: "STALE" } }, {}, {}],
    });
  });
  it("filters historical evidence and rejects unknown stops", () => {
    expect(response("reliability?route_id=Blue").body).toMatchObject({
      data: [],
    });
    expect(response("stops/missing/arrivals").status).toBe(404);
  });
  it("calculates risk from the supplied buffer instead of returning a canned result", () => {
    const base =
      "transfer-risk?arriving_route_id=Red&connecting_route_id=Orange&arriving_stop_id=Harvard&connecting_stop_id=DowntownCrossing&planned_arrival=2026-07-24T14:00:00Z";
    expect(
      response(base + "&planned_departure=2026-07-24T14:30:00Z").body,
    ).toMatchObject({
      data: { risk_band: "LOW", missed_transfer_probability: 0 },
    });
    expect(
      response(base + "&planned_departure=2026-07-24T14:01:00Z").body,
    ).toMatchObject({ data: { risk_band: "HIGH" } });
    expect(response(base + "&planned_departure=invalid").status).toBe(422);
  });
});
