"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrivalBoard, type Arrival } from "@/components/arrival-board";
import { LoadingSkeleton, StatePanel } from "@/components/trust";
import {
  liveArrivals,
  scheduledArrivals,
  serviceDate,
  formatGtfsTime,
  formatTimestamp,
} from "@/lib/rider-data";
import { useLiveQuery } from "@/lib/use-live-query";
import { publicEnv } from "@/lib/env";

export function StopArrivals({ stopId }: { stopId: string }) {
  const scheduled = useQuery({
    queryKey: ["scheduled-arrivals", stopId],
    queryFn: () => scheduledArrivals(stopId, serviceDate()),
  });
  const live = useLiveQuery({
    key: ["live-arrivals", stopId],
    fetcher: () => liveArrivals(stopId),
    streamUrl: `${publicEnv.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/live/events?stop_id=${encodeURIComponent(stopId)}`,
  });
  if (scheduled.isLoading || live.isLoading)
    return <LoadingSkeleton label="Loading arrivals" />;
  if (scheduled.isError)
    return (
      <StatePanel kind="unknown" title="Scheduled departures unavailable">
        Try again shortly. We cannot show an arrival board without the published
        schedule.
      </StatePanel>
    );
  const liveByTrip = new Map(
    (live.data ?? []).map((value) => [value.trip_id, value]),
  );
  const arrivals: Arrival[] = (scheduled.data ?? []).map((value) => {
    const prediction = liveByTrip.get(value.trip_id);
    const predicted =
      prediction?.agency_prediction?.arrival_time ??
      prediction?.agency_prediction?.departure_time;
    return {
      tripId: value.trip_id,
      routeId: value.route_id,
      destination: value.headsign,
      scheduled: formatGtfsTime(value.scheduled.gtfs_seconds),
      prediction: predicted ? formatTimestamp(predicted) : undefined,
      freshness:
        prediction?.freshness.state === "STALE"
          ? "stale"
          : prediction
            ? "live"
            : undefined,
      fallback: !prediction,
    };
  });
  return (
    <div className="space-y-4">
      {live.isError ? (
        <StatePanel kind="fallback" title="Live predictions unavailable">
          Scheduled departures remain visible while realtime information
          reconnects.
        </StatePanel>
      ) : null}
      <ArrivalBoard arrivals={arrivals} />
    </div>
  );
}
