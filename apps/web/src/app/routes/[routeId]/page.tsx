import { AppShell } from "@/components/app-shell";
import { TransitMap } from "@/components/transit-map";
import { StatePanel } from "@/components/trust";
import { RouteBadge } from "@/components/route-badge";

export default async function RoutePage({
  params,
}: {
  params: Promise<{ routeId: string }>;
}) {
  const { routeId } = await params;
  return (
    <AppShell>
      <header className="flex items-center gap-3">
        <RouteBadge label={routeId} />
        <div>
          <p className="text-brand text-sm font-semibold">Route</p>
          <h1 className="text-3xl font-semibold">{routeId}</h1>
        </div>
      </header>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <TransitMap routeName={routeId} />
        <section className="card">
          <h2 className="text-xl font-semibold">Stops and vehicles</h2>
          <p className="text-muted mt-2">
            Select a direction when schedule data is available. Vehicles are
            removed when their live data expires.
          </p>
          <StatePanel kind="fallback" title="Scheduled service">
            Live vehicles are unavailable; scheduled information remains clearly
            labeled.
          </StatePanel>
        </section>
      </div>
    </AppShell>
  );
}
