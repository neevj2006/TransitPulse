"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RouteBadge } from "@/components/route-badge";
import { LoadingSkeleton, StatePanel } from "@/components/trust";
import { searchNetwork, type SearchResult } from "@/lib/search";

const hrefFor = (result: SearchResult) =>
  result.kind === "route"
    ? `/routes/${encodeURIComponent(result.id)}`
    : result.kind === "stop"
      ? `/stops/${encodeURIComponent(result.id)}`
      : `/search?q=${encodeURIComponent(result.label)}`;

export function UniversalSearch({
  initialQuery = "",
}: {
  initialQuery?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [debounced, setDebounced] = useState(initialQuery);
  const statusId = useId();
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);
  const result = useQuery({
    queryKey: ["network-search", debounced],
    queryFn: () => searchNetwork(debounced),
    enabled: debounced.length > 1,
  });
  const groups = result.data?.reduce<
    Record<SearchResult["kind"], SearchResult[]>
  >(
    (all, item) => {
      all[item.kind].push(item);
      return all;
    },
    { route: [], stop: [], destination: [] },
  );
  return (
    <div className="space-y-3">
      <label className="font-semibold" htmlFor="network-search">
        Search routes, stops, or destinations
      </label>
      <input
        id="network-search"
        role="combobox"
        aria-expanded={Boolean(debounced && !result.isError)}
        aria-controls={statusId}
        aria-autocomplete="list"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="bg-surface border-border-strong min-h-12 w-full rounded-md border px-4"
        placeholder="Try Red Line, Harvard, or Alewife"
      />
      <p id={statusId} className="text-muted text-sm" aria-live="polite">
        {result.isFetching
          ? "Searching network…"
          : debounced.length <= 1
            ? "Enter at least two characters to search the scheduled network."
            : result.isError
              ? "Search is temporarily unavailable."
              : `${result.data?.length ?? 0} results`}
      </p>
      {result.isFetching ? (
        <LoadingSkeleton label="Searching routes and stops" />
      ) : result.isError ? (
        <StatePanel kind="unknown" title="Search unavailable">
          Check your connection and try again. Scheduled search results return
          when the service is available.
        </StatePanel>
      ) : debounced.length > 1 && !result.data?.length ? (
        <StatePanel
          kind="empty"
          title="No matching routes, stops, or destinations"
        >
          Try a route name, a stop name, or fewer words.
        </StatePanel>
      ) : groups ? (
        <div className="divide-y rounded-lg border">
          {(["route", "stop", "destination"] as const).map((kind) =>
            groups[kind].length ? (
              <section
                key={kind}
                aria-labelledby={`${kind}-results`}
                className="p-3"
              >
                <h2
                  id={`${kind}-results`}
                  className="text-muted text-sm font-semibold capitalize"
                >
                  {kind === "destination" ? "Destinations" : `${kind}s`}
                </h2>
                <ul className="mt-2 space-y-1">
                  {groups[kind].map((item) => (
                    <li key={`${item.kind}-${item.id}`}>
                      <Link
                        className="hover:bg-surface-muted flex min-h-11 items-center gap-3 rounded-md px-2 py-2"
                        href={hrefFor(item)}
                      >
                        {item.kind === "route" ? (
                          <RouteBadge
                            label={item.label}
                            color={item.route_color}
                          />
                        ) : (
                          <span className="font-medium">{item.label}</span>
                        )}
                        <span className="text-muted text-sm">
                          {item.detail}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null,
          )}
        </div>
      ) : null}
    </div>
  );
}
