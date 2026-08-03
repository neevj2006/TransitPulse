"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { z } from "zod";
import { apiRequest } from "@/lib/api";
import { LoadingSkeleton, StatePanel } from "@/components/trust";

const responseSchema = z.object({
  data: z.object({
    sufficient_data: z.boolean(),
    missed_transfer_probability: z.number().nullable(),
    risk_band: z.enum(["LOW", "MEDIUM", "HIGH", "UNKNOWN"]),
    planned_buffer_seconds: z.number(),
    walking_seconds: z.number(),
    walking_time_source: z.string(),
    sample_size: z.number(),
    arrival_sample_size: z.number(),
    departure_sample_size: z.number(),
    source_first_at: z.string().nullable(),
    source_last_at: z.string().nullable(),
    history_stale: z.boolean(),
    assumptions: z.array(z.string()),
  }),
  meta: z.object({ calculation_version: z.string() }),
});

const formatMinutes = (seconds: number) => {
  const sign = seconds < 0 ? "−" : "";
  return `${sign}${Math.abs(Math.round(seconds / 60))} min`;
};

const nowForInput = () => new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16);

export function TransferRiskCalculator() {
  const [arrivingRoute, setArrivingRoute] = useState("Red");
  const [arrivingStop, setArrivingStop] = useState("Harvard");
  const [connectingRoute, setConnectingRoute] = useState("Orange");
  const [connectingStop, setConnectingStop] = useState("DowntownCrossing");
  const [arrival, setArrival] = useState(nowForInput);
  const [departure, setDeparture] = useState("");
  const [walking, setWalking] = useState("3");
  const [submitted, setSubmitted] = useState(false);
  const canCalculate = Boolean(arrival && departure && arrivingRoute && arrivingStop && connectingRoute && connectingStop);
  const params = new URLSearchParams({
    arriving_route_id: arrivingRoute,
    arriving_stop_id: arrivingStop,
    connecting_route_id: connectingRoute,
    connecting_stop_id: connectingStop,
    planned_arrival: new Date(arrival).toISOString(),
    planned_departure: departure ? new Date(departure).toISOString() : "",
    ...(walking ? { walking_seconds: String(Number(walking) * 60) } : {}),
  });
  const query = useQuery({
    queryKey: ["transfer-risk", params.toString()],
    enabled: submitted && canCalculate,
    queryFn: () => apiRequest(`/api/v1/transfer-risk?${params}`, responseSchema),
  });
  return (
    <div className="mt-6 space-y-6">
      <form
        className="card grid gap-4 md:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(true);
        }}
      >
        <fieldset className="contents">
          <legend className="sr-only">Transfer details</legend>
          <label className="text-sm font-medium">Arriving route
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" value={arrivingRoute} onChange={(event) => setArrivingRoute(event.target.value)} required />
          </label>
          <label className="text-sm font-medium">Arriving stop
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" value={arrivingStop} onChange={(event) => setArrivingStop(event.target.value)} required />
          </label>
          <label className="text-sm font-medium">Connecting route
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" value={connectingRoute} onChange={(event) => setConnectingRoute(event.target.value)} required />
          </label>
          <label className="text-sm font-medium">Connecting stop
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" value={connectingStop} onChange={(event) => setConnectingStop(event.target.value)} required />
          </label>
          <label className="text-sm font-medium">Planned arrival
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" type="datetime-local" value={arrival} onChange={(event) => setArrival(event.target.value)} required />
          </label>
          <label className="text-sm font-medium">Planned connecting departure
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)} required />
          </label>
          <label className="text-sm font-medium">Walking time (minutes)
            <input className="mt-1 block w-full rounded-md border bg-surface p-3" type="number" min="0" max="60" value={walking} onChange={(event) => setWalking(event.target.value)} />
            <span className="text-muted mt-1 block font-normal">Use your own estimate for elevators, platforms, and mobility needs.</span>
          </label>
        </fieldset>
        <div className="md:col-span-2">
          <button className="bg-brand-strong min-h-11 rounded-md px-4 py-2 font-semibold text-white disabled:opacity-60" disabled={!canCalculate} type="submit">Calculate transfer risk</button>
        </div>
      </form>
      {query.isPending ? <LoadingSkeleton label="Calculating transfer risk" /> : null}
      {query.isError ? <StatePanel kind="offline" title="Transfer-risk data is unavailable">We cannot safely estimate this transfer right now. Check scheduled times and try again later.</StatePanel> : null}
      {query.data ? <TransferRiskResult value={query.data} /> : null}
    </div>
  );
}

function TransferRiskResult({ value }: { value: z.infer<typeof responseSchema> }) {
  const result = value.data;
  if (!result.sufficient_data) return <StatePanel kind="empty" title="Not enough data to estimate transfer risk">We found {result.arrival_sample_size} arrival and {result.departure_sample_size} departure observations. A probability requires at least 20 for each leg, so TransitPulse will not guess.</StatePanel>;
  const percentage = Math.round((result.missed_transfer_probability ?? 0) * 100);
  const tone = result.risk_band === "LOW" ? "text-status-success" : result.risk_band === "MEDIUM" ? "text-status-warning" : "text-status-error";
  return <section className="card" aria-labelledby="transfer-result">
    <p className="text-muted text-sm font-semibold">Empirical transfer baseline</p>
    <h2 id="transfer-result" className={`mt-1 text-3xl font-semibold ${tone}`}>{result.risk_band[0] + result.risk_band.slice(1).toLowerCase()} risk · {percentage}% estimated missed-transfer probability</h2>
    <p className="mt-3">Your planned buffer is <strong>{formatMinutes(result.planned_buffer_seconds)}</strong> after {formatMinutes(result.walking_seconds)} of walking. This is an estimate from historical agency predictions, not a guarantee.</p>
    {result.history_stale ? <StatePanel kind="stale" title="Historical data may be stale">The most recent sample is older than seven days. Treat this result as context, not live guidance.</StatePanel> : null}
    <dl className="mt-5 grid gap-4 sm:grid-cols-3">
      <div><dt className="text-muted text-sm">Samples per leg</dt><dd className="mt-1 text-xl font-semibold">{result.sample_size}</dd></div>
      <div><dt className="text-muted text-sm">Data range</dt><dd className="mt-1 text-sm font-semibold">{result.source_first_at ? new Date(result.source_first_at).toLocaleDateString() : "Unknown"} to {result.source_last_at ? new Date(result.source_last_at).toLocaleDateString() : "Unknown"}</dd></div>
      <div><dt className="text-muted text-sm">Calculation version</dt><dd className="mt-1 text-sm font-semibold">{value.meta.calculation_version}</dd></div>
    </dl>
    <h3 className="mt-5 font-semibold">Assumptions</h3>
    <ul className="text-muted mt-2 list-disc space-y-1 pl-5 text-sm">{result.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul>
  </section>;
}
