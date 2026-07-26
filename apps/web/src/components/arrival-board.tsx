import { RouteBadge } from "@/components/route-badge";
import { SourceBadge, StatePanel } from "@/components/trust";

export type Arrival = {
  tripId: string;
  routeId: string;
  destination?: string | null;
  scheduled?: string;
  prediction?: string;
  freshness?: "live" | "stale";
  fallback?: boolean;
};
export function ArrivalBoard({ arrivals }: { arrivals: Arrival[] }) {
  if (!arrivals.length)
    return (
      <StatePanel kind="empty" title="No upcoming service">
        There is no scheduled service at this stop right now.
      </StatePanel>
    );
  return (
    <section className="card">
      <h2 className="text-xl font-semibold">Upcoming departures</h2>
      <ul className="mt-3 divide-y">
        {arrivals.map((arrival) => (
          <li
            className="flex flex-wrap items-center justify-between gap-3 py-3"
            key={arrival.tripId}
          >
            <div className="flex items-center gap-3">
              <RouteBadge label={arrival.routeId} />
              <span>{arrival.destination ?? "Destination unavailable"}</span>
            </div>
            <div className="text-right">
              <p className="font-mono font-semibold">
                {arrival.prediction ?? arrival.scheduled ?? "Unknown"}
              </p>
              <SourceBadge
                kind={
                  arrival.fallback
                    ? "scheduled"
                    : (arrival.freshness ?? "unknown")
                }
                age={arrival.fallback ? "live unavailable" : undefined}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
