"use client";

import { useMemo, useState } from "react";
import type { Feature, Point } from "geojson";
import { useLiveQuery } from "@/lib/use-live-query";
import { publicEnv } from "@/lib/env";
import { systemVehicles, type RiderVehicle } from "@/lib/rider-data";
import { TransitMap } from "@/components/transit-map";
import { VehicleList } from "@/components/vehicle-list";
import { LoadingSkeleton, StatePanel } from "@/components/trust";

export function LiveSystemMap() {
  const [route, setRoute] = useState("");
  const [state, setState] = useState("all");
  const query = useLiveQuery({
    key: ["system-vehicles"],
    fetcher: systemVehicles,
    streamUrl: `${publicEnv.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/live/events`,
  });
  const values = useMemo(
    () =>
      (query.data ?? []).filter(
        (value) =>
          (!route ||
            value.route_id?.toLowerCase().includes(route.toLowerCase())) &&
          (state === "all" ||
            (state === "live"
              ? value.freshness.state === "HEALTHY"
              : value.freshness.state === "STALE")),
      ),
    [query.data, route, state],
  );
  const points: Feature<Point>[] = values.map((value) => ({
    type: "Feature",
    properties: { id: value.vehicle_id, freshness: value.freshness.state },
    geometry: { type: "Point", coordinates: [value.longitude, value.latitude] },
  }));
  if (query.isLoading)
    return <LoadingSkeleton label="Loading live vehicle locations" />;
  if (query.isError)
    return (
      <StatePanel kind="offline" title="Live vehicle locations unavailable">
        Use scheduled route and stop information while the realtime feed
        reconnects.
      </StatePanel>
    );
  return (
    <div className="space-y-4">
      <section className="card flex flex-wrap gap-3" aria-label="Map filters">
        <label className="grid gap-1 text-sm font-semibold">
          Route
          <input
            className="bg-surface min-h-11 rounded-md border px-3 font-normal"
            value={route}
            onChange={(event) => setRoute(event.target.value)}
            placeholder="Any route"
          />
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Freshness
          <select
            className="bg-surface min-h-11 rounded-md border px-3 font-normal"
            value={state}
            onChange={(event) => setState(event.target.value)}
          >
            <option value="all">All states</option>
            <option value="live">Live only</option>
            <option value="stale">Stale only</option>
          </select>
        </label>
      </section>
      <TransitMap routeName="MBTA network" vehicles={points} />
      <VehicleList vehicles={values.map(toVehicle)} />
    </div>
  );
}

function toVehicle(value: RiderVehicle) {
  return {
    id: value.vehicle_id,
    route: value.route_id ?? "Route unknown",
    nextStop: value.trip_id ? `Trip ${value.trip_id}` : undefined,
    state:
      value.freshness.state === "HEALTHY"
        ? ("live" as const)
        : ("stale" as const),
  };
}
