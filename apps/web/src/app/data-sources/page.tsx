import { AppShell } from "@/components/app-shell";
export default function DataSourcesPage() {
  return (
    <AppShell>
      <article className="max-w-3xl space-y-4">
        <h1 className="text-3xl font-semibold">Data sources</h1>
        <p>
          Transit data provided by MassDOT/MBTA. TransitPulse is an independent
          project and is not affiliated with or endorsed by MBTA.
        </p>
        <p className="text-muted">
          Map data © OpenStreetMap contributors. Tiles by OpenFreeMap. Data
          timestamps and known limitations are displayed with relevant results.
        </p>
      </article>
    </AppShell>
  );
}
