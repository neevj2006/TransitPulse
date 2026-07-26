import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { NearbyStops } from "@/components/nearby-stops";
import { ServiceAlert, SourceBadge } from "@/components/trust";
import { UniversalSearch } from "@/components/universal-search";

export default function Home() {
  return (
    <AppShell>
      <div className="space-y-8">
        <section className="max-w-3xl">
          <p className="text-brand text-sm font-semibold">
            Boston transit, clearly explained
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            Know what is scheduled, live, and uncertain.
          </h1>
          <p className="text-muted mt-4 text-lg leading-7">
            TransitPulse keeps MBTA schedule and realtime information visibly
            distinct so you can make informed choices.
          </p>
          <div className="mt-6">
            <UniversalSearch />
          </div>
        </section>
        <section
          aria-label="Network status"
          className="card flex flex-wrap items-center justify-between gap-3"
        >
          <div>
            <h2 className="font-semibold">Network status</h2>
            <p className="text-muted text-sm">
              Realtime feeds will appear here when available.
            </p>
          </div>
          <SourceBadge kind="unknown" />
        </section>
        <ServiceAlert title="Service alerts">
          <span>
            Agency alerts will be shown here with their original source and
            update time.
          </span>
        </ServiceAlert>
        <section className="grid gap-4 md:grid-cols-2">
          <NearbyStops />
          <Link className="card hover:bg-surface-muted block" href="/map">
            <h2 className="font-semibold">Explore the live map</h2>
            <p className="text-muted mt-1 text-sm">
              Use the accompanying lists if a map is unavailable.
            </p>
          </Link>
        </section>
      </div>
    </AppShell>
  );
}
