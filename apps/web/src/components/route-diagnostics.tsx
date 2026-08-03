"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { AccessibleLineChart } from "@/components/accessible-chart";
import { apiRequest } from "@/lib/api";
import { LoadingSkeleton, StatePanel } from "@/components/trust";

const schema = z.object({
  data: z.array(
    z.object({
      route_id: z.string().nullable(),
      direction_id: z.number(),
      stop_id: z.string(),
      hour: z.number(),
      sample_size: z.number(),
      coverage: z.number(),
      median_delay_seconds: z.number().nullable(),
      p95_delay_seconds: z.number().nullable(),
    }),
  ),
});

export function RouteDiagnostics() {
  const query = useQuery({
    queryKey: ["route-diagnostics"],
    queryFn: () => apiRequest("/api/v1/reliability", schema),
  });
  if (query.isPending)
    return <LoadingSkeleton label="Loading route diagnostics" />;
  if (query.isError)
    return (
      <StatePanel kind="offline" title="Route diagnostics unavailable">
        Retained reliability evidence could not be loaded.
      </StatePanel>
    );
  const rows = query.data.data;
  if (!rows.length)
    return (
      <StatePanel kind="empty" title="No retained route evidence">
        Diagnostics appear after observed predictions are retained.
      </StatePanel>
    );
  const chronic = [...rows]
    .filter((row) => row.p95_delay_seconds !== null)
    .sort((a, b) => (b.p95_delay_seconds ?? 0) - (a.p95_delay_seconds ?? 0))
    .slice(0, 10);
  const coverage =
    rows.reduce((total, row) => total + row.coverage, 0) / rows.length;
  return (
    <div className="space-y-6">
      <AccessibleLineChart
        title="Observed delay distribution"
        takeaway="Median delay by route, direction, and observed hour. This is evidence, not a service incident declaration."
        data={rows.map((row) => ({
          label: `${row.route_id ?? "Unknown"} · dir ${row.direction_id} · ${row.hour}:00`,
          value: Math.round((row.median_delay_seconds ?? 0) / 60),
        }))}
        coverage={`${Math.round(coverage * 100)}%`}
      />
      <section className="card overflow-x-auto">
        <h2 className="text-xl font-semibold">Chronic-delay stop candidates</h2>
        <p className="text-muted mt-1 text-sm">
          Highest retained p95 delay, with coverage and sample context.
        </p>
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr>
              <th>Route</th>
              <th>Stop</th>
              <th>Hour</th>
              <th>P95 delay</th>
              <th>Coverage</th>
              <th>Samples</th>
            </tr>
          </thead>
          <tbody>
            {chronic.map((row, index) => (
              <tr className="border-t" key={`${row.stop_id}-${index}`}>
                <td className="py-2">{row.route_id}</td>
                <td>{row.stop_id || "Unspecified"}</td>
                <td>{row.hour}:00</td>
                <td>{Math.round((row.p95_delay_seconds ?? 0) / 60)} min</td>
                <td>{Math.round(row.coverage * 100)}%</td>
                <td>{row.sample_size}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <StatePanel
        kind="unknown"
        title="Headway, bunching, and possible missing trips"
      >
        These measures are intentionally unavailable until observations can be
        matched to complete scheduled service. TransitPulse will label them as
        uncertain inferences—not confirmed missed trips—when that evidence
        exists.{" "}
        <a className="text-brand underline" href="/operator/feeds">
          Review source-health context.
        </a>
      </StatePanel>
    </div>
  );
}
