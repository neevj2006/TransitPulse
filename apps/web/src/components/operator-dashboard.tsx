"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/lib/api";
import { LoadingSkeleton, StatePanel } from "@/components/trust";

const schema = z.object({
  data: z.array(
    z.object({
      source_id: z.string(),
      state: z.string().optional(),
      last_success_at: z.string().nullable().optional(),
      entity_counts: z.object({ accepted: z.number() }).optional(),
      rejection_counts: z
        .object({ parser_errors: z.number(), unreconciled: z.number() })
        .optional(),
    }),
  ),
  meta: z.object({
    generated_at: z.string(),
    api_latency: z.object({
      p50_ms: z.number().nullable(),
      p95_ms: z.number().nullable(),
    }),
    cache_telemetry: z
      .object({ key_count: z.number(), memory_bytes: z.number() })
      .nullable(),
  }),
});
const shown = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : "No successful poll";

export function OperatorDashboard({
  view,
}: {
  view: "feeds" | "system" | "routes" | "overview";
}) {
  const query = useQuery({
    queryKey: ["operator-health"],
    queryFn: () => apiRequest("/api/v1/live/health", schema),
    refetchInterval: 30_000,
  });
  if (query.isPending)
    return <LoadingSkeleton label="Loading operator health data" />;
  if (query.isError)
    return (
      <StatePanel kind="offline" title="Operator data unavailable">
        No credentials, internal hosts, or raw errors are exposed.
      </StatePanel>
    );
  if (view === "routes")
    return (
      <section className="card">
        <h2 className="text-xl font-semibold">Route diagnostics</h2>
        <p className="text-muted mt-2">
          Observed delay and coverage are available in Reliability. Headway,
          bunching, and possible missing trips are withheld until complete
          schedule matching is available; they are never presented as confirmed
          incidents.
        </p>
        <a
          className="text-brand mt-4 inline-block underline"
          href="/reliability"
        >
          Open reliability evidence
        </a>
      </section>
    );
  const { data, meta } = query.data;
  if (view === "system")
    return (
      <section className="grid gap-4 sm:grid-cols-2">
        <Metric
          label="API p50"
          value={
            meta.api_latency.p50_ms === null
              ? "No samples"
              : `${meta.api_latency.p50_ms} ms`
          }
        />
        <Metric
          label="API p95"
          value={
            meta.api_latency.p95_ms === null
              ? "No samples"
              : `${meta.api_latency.p95_ms} ms`
          }
        />
        <Metric
          label="Cache keys"
          value={
            meta.cache_telemetry?.key_count?.toLocaleString() ?? "Unavailable"
          }
        />
        <Metric
          label="Cache memory"
          value={
            meta.cache_telemetry
              ? `${Math.round(meta.cache_telemetry.memory_bytes / 1024)} KB`
              : "Unavailable"
          }
        />
      </section>
    );
  return (
    <div className="space-y-6">
      <p className="text-muted text-sm">
        Updated {shown(meta.generated_at)}. Status reflects source evidence.
      </p>
      <section className="card overflow-x-auto">
        <table className="w-full min-w-180 text-left text-sm">
          <caption className="sr-only">Current feed health</caption>
          <thead>
            <tr className="border-b">
              <th className="p-3">Source</th>
              <th className="p-3">Status</th>
              <th className="p-3">Last success</th>
              <th className="p-3">Entities</th>
              <th className="p-3">Failures</th>
            </tr>
          </thead>
          <tbody>
            {data.map((source) => (
              <tr className="border-b" key={source.source_id}>
                <th className="p-3">{source.source_id}</th>
                <td className="p-3">{source.state ?? "Unknown"}</td>
                <td className="p-3">{shown(source.last_success_at)}</td>
                <td className="p-3 font-mono">
                  {source.entity_counts?.accepted ?? 0}
                </td>
                <td className="p-3 font-mono">
                  parser {source.rejection_counts?.parser_errors ?? 0};
                  reconcile {source.rejection_counts?.unreconciled ?? 0}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <article className="card">
      <p className="text-muted text-sm">{label}</p>
      <p className="mt-2 font-mono text-2xl font-semibold">{value}</p>
    </article>
  );
}
