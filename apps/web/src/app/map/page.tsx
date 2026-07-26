import { AppShell } from "@/components/app-shell";
import { TransitMap } from "@/components/transit-map";
import { StatePanel } from "@/components/trust";
import { VehicleList } from "@/components/vehicle-list";

export default function MapPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <header>
          <p className="text-brand text-sm font-semibold">Live network</p>
          <h1 className="mt-1 text-3xl font-semibold">Transit map</h1>
          <p className="text-muted mt-2">
            Map data is an enhancement; the current vehicle list remains
            available below.
          </p>
        </header>
        <TransitMap routeName="MBTA network" />
        <VehicleList vehicles={[]} />
        <StatePanel kind="stale" title="Last-known locations expire">
          Stale vehicles are never presented as live and are removed after the
          configured TTL.
        </StatePanel>
      </div>
    </AppShell>
  );
}
