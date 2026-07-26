import { AppShell } from "@/components/app-shell";
import { StopArrivals } from "@/components/stop-arrivals";

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
      <div className="mt-6">
        <StopArrivals stopId={stopId} />
      </div>
    </AppShell>
  );
}
