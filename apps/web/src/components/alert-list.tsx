"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useLiveQuery } from "@/lib/use-live-query";
import { alerts, formatTimestamp } from "@/lib/rider-data";
import { publicEnv } from "@/lib/env";
import { LoadingSkeleton, SourceBadge, StatePanel } from "@/components/trust";

export function AlertList() {
  const [filter, setFilter] = useState("");
  const query = useLiveQuery({
    key: ["alerts"],
    fetcher: () => alerts(),
    streamUrl: `${publicEnv.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/live/events`,
  });
  const items = useMemo(
    () =>
      (query.data ?? []).filter((item) =>
        `${item.header ?? ""} ${item.effect ?? ""} ${item.route_ids.join(" ")} ${item.stop_ids.join(" ")}`
          .toLowerCase()
          .includes(filter.toLowerCase()),
      ),
    [query.data, filter],
  );
  return (
    <div className="mt-6 space-y-4">
      <label
        className="grid max-w-md gap-2 font-semibold"
        htmlFor="alert-filter"
      >
        Filter agency alerts
        <input
          id="alert-filter"
          className="bg-surface border-border-strong min-h-11 rounded-md border px-3 font-normal"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Route, stop, or effect"
        />
      </label>
      <p className="text-muted text-sm">
        Filter by route, stop, effect, severity, or active period. Agency text
        is shown without generated summaries.
      </p>
      {query.isLoading ? (
        <LoadingSkeleton label="Loading agency alerts" />
      ) : query.isError ? (
        <StatePanel kind="unknown" title="Alerts unavailable">
          Agency notices could not be loaded. Try again shortly.
        </StatePanel>
      ) : !items.length ? (
        <StatePanel kind="empty" title="No active alerts">
          {filter
            ? "No active alerts match this filter. Clear it to see all current agency notices."
            : "When available, agency-provided notices will show their effect, affected routes, and source age."}
        </StatePanel>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li className="card" key={item.alert_id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">
                    {item.header ?? "Agency service alert"}
                  </h2>
                  <p className="text-muted mt-1 text-sm">
                    {item.effect ?? "Effect not specified"} · Updated{" "}
                    {formatTimestamp(item.source_timestamp)}
                  </p>
                </div>
                <SourceBadge
                  kind={item.freshness.state === "STALE" ? "stale" : "live"}
                />
              </div>
              {item.description ? (
                <p className="mt-3 text-sm leading-6 whitespace-pre-wrap">
                  {item.description}
                </p>
              ) : null}
              <p className="text-muted mt-3 text-sm">
                Affected:{" "}
                {[...item.route_ids, ...item.stop_ids].map((id) => (
                  <Link
                    className="mr-2 underline"
                    href={
                      item.route_ids.includes(id)
                        ? `/routes/${encodeURIComponent(id)}`
                        : `/stops/${encodeURIComponent(id)}`
                    }
                    key={id}
                  >
                    {id}
                  </Link>
                ))}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
