"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DeferredTransitMap } from "@/components/deferred-transit-map";
import { VehicleList } from "@/components/vehicle-list";
import { LoadingSkeleton, StatePanel } from "@/components/trust";
import { routeStops, routeVehicles } from "@/lib/rider-data";
import { useLiveQuery } from "@/lib/use-live-query";
import { publicEnv } from "@/lib/env";

export function RouteDetail({ routeId }: { routeId: string }) {
  const [direction, setDirection] = useState<number>();
  const stops = useQuery({
    queryKey: ["route-stops", routeId, direction],
    queryFn: () => routeStops(routeId, direction),
  });
  const vehicles = useLiveQuery({
    key: ["route-vehicles", routeId],
    fetcher: () => routeVehicles(routeId),
    streamUrl: `${publicEnv.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/live/events?route_id=${encodeURIComponent(routeId)}`,
  });
  if (stops.isLoading || vehicles.isLoading)
    return <LoadingSkeleton label="Loading route information" />;
  if (stops.isError)
    return (
      <StatePanel kind="unknown" title="Route schedule unavailable">
        Route stops and scheduled service could not be loaded.
      </StatePanel>
    );
  if (!stops.data)
    return (
      <StatePanel kind="unknown" title="Route schedule unavailable">
        Route stops and scheduled service could not be loaded.
      </StatePanel>
    );
  const routeData = stops.data;
  const liveVehicles = vehicles.data ?? [];
  return (
    <div className="mt-6 space-y-6">
      {routeData.directions.length > 1 ? (
        <fieldset className="card">
          <legend className="font-semibold">Direction</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {routeData.directions.map((item) => (
              <button
                className="bg-surface-muted min-h-11 rounded-md px-3"
                aria-pressed={direction === item}
                onClick={() => setDirection(item)}
                key={item}
              >
                Direction {item}
              </button>
            ))}
          </div>
        </fieldset>
      ) : null}
      <div className="grid gap-6 lg:grid-cols-2">
        <DeferredTransitMap routeName={routeId} />
        <section className="card" id="stop-list">
          <h2 className="text-xl font-semibold">
            Stops{routeData.headsign ? ` toward ${routeData.headsign}` : ""}
          </h2>
          <ol className="mt-3 divide-y">
            {routeData.stops.map((stop) => (
              <li
                className="flex min-h-11 items-center gap-3 py-2"
                key={stop.stop_id}
              >
                <span className="text-muted tabular-nums">{stop.sequence}</span>
                <Link
                  className="underline"
                  href={`/stops/${encodeURIComponent(stop.stop_id)}`}
                >
                  {stop.name}
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </div>
      {vehicles.isError ? (
        <StatePanel kind="fallback" title="Live vehicles unavailable">
          Scheduled route stops remain visible while realtime information
          reconnects.
        </StatePanel>
      ) : (
        <VehicleList
          vehicles={liveVehicles.map((item) => ({
            id: item.vehicle_id,
            route: item.route_id ?? routeId,
            nextStop: item.trip_id ? `Trip ${item.trip_id}` : undefined,
            state:
              item.freshness.state === "HEALTHY"
                ? ("live" as const)
                : ("stale" as const),
          }))}
        />
      )}
    </div>
  );
}
