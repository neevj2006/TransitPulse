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
      </article>
    </AppShell>
  );
}
