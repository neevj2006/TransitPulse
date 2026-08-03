"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { z } from "zod";
import { apiRequest } from "@/lib/api";
import { AccessibleLineChart } from "@/components/accessible-chart";
import { LoadingSkeleton, StatePanel } from "@/components/trust";

const responseSchema = z.object({
  data: z.array(
    z.object({
      route_id: z.string().nullable(),
      service_date: z.string(),
      hour: z.number(),
      sample_size: z.number(),
      coverage: z.number(),
      median_delay_seconds: z.number().nullable(),
      p95_delay_seconds: z.number().nullable(),
      on_time_percentage: z.number().nullable(),
    }),
  ),
  meta: z.object({
    metric_definition: z.string(),
    minimum_sample_size: z.number(),
    minimum_coverage: z.number(),
  }),
});

const duration = (value: number | null) =>
  value === null ? "—" : `${Math.round(value / 60)} min`;

export function ReliabilityDashboard() {
  const [routeId, setRouteId] = useState("");
  const [weekday, setWeekday] = useState("");
  const [directionId, setDirectionId] = useState("");
  const [stopId, setStopId] = useState("");
  const [hour, setHour] = useState("");
  const queryString = new URLSearchParams({
    ...(routeId ? { route_id: routeId } : {}),
    ...(weekday ? { weekday } : {}),
    ...(directionId ? { direction_id: directionId } : {}),
    ...(stopId ? { stop_id: stopId } : {}),
    ...(hour ? { hour } : {}),
  }).toString();
  const query = useQuery({
    queryKey: ["reliability", queryString],
    queryFn: () =>
      apiRequest(
        `/api/v1/reliability${queryString ? `?${queryString}` : ""}`,
        responseSchema,
      ),
  });
  if (query.isPending)
    return <LoadingSkeleton label="Loading historical reliability" />;
  if (query.isError)
    return (
      <StatePanel kind="offline" title="Historical metrics unavailable">
        Try again when the history service is available.
      </StatePanel>
    );
  const rows = query.data.data;
  if (!rows.length)
    return (
      <StatePanel kind="empty" title="Not enough data yet">
        Historical reliability appears after sufficient observed trip updates
        are retained.
      </StatePanel>
    );
  const samples = rows.reduce((total, row) => total + row.sample_size, 0);
  const coverage =
    rows.reduce((total, row) => total + row.coverage, 0) / rows.length;
  const median =
    rows.find((row) => row.median_delay_seconds !== null)
      ?.median_delay_seconds ?? null;
  const p95 =
    rows.find((row) => row.p95_delay_seconds !== null)?.p95_delay_seconds ??
    null;
  const onTime =
    rows.find((row) => row.on_time_percentage !== null)?.on_time_percentage ??
    null;
  const dates = rows.map((row) => row.service_date).sort();
  return (
    <div className="mt-6 space-y-6">
      <fieldset className="card flex flex-wrap gap-4">
        <legend className="px-1 font-semibold">Filters</legend>
        <label className="text-sm">
          Route{" "}
          <input
            className="ml-2 rounded-md border p-2"
            value={routeId}
            onChange={(event) => setRouteId(event.target.value)}
            placeholder="e.g. Red"
          />
        </label>
        <label className="text-sm">
          Direction{" "}
          <select
            className="ml-2 rounded-md border p-2"
            value={directionId}
            onChange={(event) => setDirectionId(event.target.value)}
          >
            <option value="">All</option>
            <option value="0">0</option>
            <option value="1">1</option>
          </select>
        </label>
        <label className="text-sm">
          Stop{" "}
          <input
            className="ml-2 rounded-md border p-2"
            value={stopId}
            onChange={(event) => setStopId(event.target.value)}
            placeholder="Stop ID"
          />
        </label>
        <label className="text-sm">
          Hour{" "}
          <select
            className="ml-2 rounded-md border p-2"
            value={hour}
            onChange={(event) => setHour(event.target.value)}
          >
            <option value="">All</option>
            {Array.from({ length: 24 }, (_, value) => (
              <option key={value} value={value}>
                {value}:00
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Weekday{" "}
          <select
            className="ml-2 rounded-md border p-2"
            value={weekday}
            onChange={(event) => setWeekday(event.target.value)}
          >
            <option value="">All</option>
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(
              (day, index) => (
                <option key={day} value={index + 1}>
                  {day}
                </option>
              ),
            )}
          </select>
        </label>
      </fieldset>
      <section
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        aria-label="Reliability summary"
      >
        {[
          ["Observed samples", samples.toLocaleString()],
          ["Coverage", `${Math.round(coverage * 100)}%`],
          ["Median delay", duration(median)],
          ["P95 delay", duration(p95)],
          ["On time", onTime === null ? "—" : `${Math.round(onTime * 100)}%`],
        ].map(([label, value]) => (
          <article className="card" key={label}>
            <p className="text-muted text-sm">{label}</p>
            <p className="mt-2 font-mono text-2xl font-semibold">{value}</p>
          </article>
        ))}
      </section>
      <AccessibleLineChart
        title="Median delay by observed hour"
        takeaway="Historical agency predictions grouped by the hour TransitPulse received them."
        data={rows.map((row) => ({
          label: `${row.service_date} ${row.hour}:00`,
          value: Math.round((row.median_delay_seconds ?? 0) / 60),
        }))}
        coverage={`${Math.round(coverage * 100)}%`}
      />
      <section className="card">
        <h2 className="text-xl font-semibold">Weekday and hour coverage</h2>
        <div className="mt-3 grid grid-cols-6 gap-2 sm:grid-cols-12">
          {rows.map((row) => (
            <div
              className="bg-surface-muted rounded-md p-2 text-xs"
              key={`${row.service_date}-${row.hour}`}
            >
              <strong>{row.hour}:00</strong>
              <br />
              {Math.round(row.coverage * 100)}% · {row.sample_size} samples
            </div>
          ))}
        </div>
        <p className="text-muted mt-3 text-sm">
          Each cell is an observed-hour table alternative; insufficient samples
          remain visible rather than inferred.
        </p>
      </section>
      <section className="card">
        <h2 className="text-xl font-semibold">Data context</h2>
        <p className="text-muted mt-2">
          Metric definition {query.data.meta.metric_definition}. Rider results
          need at least {query.data.meta.minimum_sample_size} samples and{" "}
          {Math.round(query.data.meta.minimum_coverage * 100)}% coverage. These
          are observed predictions, not confirmed cancellations.
        </p>
        <p className="text-muted mt-2 text-sm">
          Collection date range: {dates[0]} to {dates.at(-1)}.
        </p>
      </section>
    </div>
  );
}
