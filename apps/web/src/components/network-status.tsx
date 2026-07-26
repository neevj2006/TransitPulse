"use client";

import { useQuery } from "@tanstack/react-query";
import { liveHealth } from "@/lib/rider-data";
import { LoadingSkeleton, SourceBadge, StatePanel } from "@/components/trust";

export function NetworkStatus() {
  const query = useQuery({
    queryKey: ["live-health"],
    queryFn: liveHealth,
    refetchInterval: 60_000,
  });
  if (query.isLoading)
    return <LoadingSkeleton label="Loading network status" />;
  if (query.isError)
    return (
      <StatePanel kind="offline" title="Network status unavailable">
        Realtime feed status could not be reached. Scheduled information remains
        available where published.
      </StatePanel>
    );
  const sources = query.data?.data ?? [];
  const unhealthy = sources.some(
    (source) =>
      String((source as { state?: string }).state).toUpperCase() !== "HEALTHY",
  );
  return (
    <section
      aria-label="Network status"
      className="card flex flex-wrap items-center justify-between gap-3"
    >
      <div>
        <h2 className="font-semibold">Network status</h2>
        <p className="text-muted text-sm">
          {sources.length
            ? `${sources.length} realtime source${sources.length === 1 ? "" : "s"} reporting.`
            : "Realtime source status is not yet available."}
        </p>
      </div>
      <SourceBadge
        kind={sources.length ? (unhealthy ? "stale" : "live") : "unknown"}
      />
    </section>
  );
}
