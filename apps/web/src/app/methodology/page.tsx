import { AppShell } from "@/components/app-shell";
export default function MethodologyPage() {
  return (
    <AppShell>
      <article className="max-w-3xl space-y-4">
        <h1 className="text-3xl font-semibold">Methodology</h1>
        <p>
          Scheduled values come from published GTFS. Live values come from fresh
          agency realtime data. Observed values describe retained history.
          TransitPulse estimates are labeled as estimates and include their
          uncertainty.
        </p>
        <p className="text-muted">
          When realtime data is stale or unavailable, TransitPulse shows the
          last update time and may fall back to clearly labeled scheduled
          information.
        </p>
        <section className="space-y-3">
          <h2 className="text-2xl font-semibold">Transfer-risk baseline</h2>
          <p>
            Transfer risk compares a planned arrival, planned connecting
            departure, and walking-time input with historical agency-predicted
            arrival and departure delays. It evaluates all pairs of retained
            delay observations independently. A result needs at least 20
            observations for each leg; otherwise TransitPulse shows “Not enough
            data” instead of a probability.
          </p>
          <p className="text-muted">
            Low risk is 15% or less estimated missed-transfer probability,
            Medium is over 15% through 35%, and High is over 35%. The estimate
            does not model platform congestion, accessibility needs, service
            disruptions, or correlations between lines, and never guarantees a
            connection. Calculation versions, sample size, and data dates are
            displayed with every result.
          </p>
        </section>
      </article>
    </AppShell>
  );
}
