import { AppShell } from "@/components/app-shell";
import { ArrivalBoard } from "@/components/arrival-board";
import { StatePanel } from "@/components/trust";

export default async function StopPage({
  params,
}: {
  params: Promise<{ stopId: string }>;
}) {
  const { stopId } = await params;
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">Stop</p>
        <h1 className="mt-1 text-3xl font-semibold">
          {decodeURIComponent(stopId)}
        </h1>
        <p className="text-muted mt-2">
          Accessibility information and location are shown when provided by the
          published GTFS feed.
        </p>
      </header>
      <div className="mt-6 space-y-4">
        <StatePanel kind="fallback" title="Live predictions unavailable">
          Scheduled departures remain visible while realtime information
          reconnects.
        </StatePanel>
        <ArrivalBoard arrivals={[]} />
      </div>
    </AppShell>
  );
}
