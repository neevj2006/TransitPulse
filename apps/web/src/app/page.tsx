import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { ServiceAlert, SourceBadge, StatePanel } from "@/components/trust";

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
          <form action="/search" className="mt-6 flex gap-2">
            <label className="sr-only" htmlFor="home-search">
              Search routes or stops
            </label>
            <input
              id="home-search"
              name="q"
              className="bg-surface border-border-strong min-h-12 min-w-0 flex-1 rounded-md border px-4"
              placeholder="Search a route or stop"
            />
            <button className="bg-brand-strong min-h-12 rounded-md px-5 font-semibold text-white">
              Search
            </button>
          </form>
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
          <StatePanel kind="empty" title="No recent places yet">
            Search for a route or stop to start exploring the network.
          </StatePanel>
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
