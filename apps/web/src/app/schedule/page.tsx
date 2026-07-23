import Link from "next/link";
import { TransitMap } from "@/components/transit-map";

const stops = [
  "Alewife",
  "Davis",
  "Porter",
  "Harvard",
  "Central",
  "Kendall/MIT",
  "Charles/MGH",
  "Park Street",
];

export default function SchedulePage() {
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 sm:p-8">
      <a className="text-brand underline" href="#content">
        Skip to content
      </a>
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-brand text-sm font-semibold">Scheduled network</p>
          <h1 className="text-3xl font-bold">Find MBTA routes and stops</h1>
          <p className="text-muted mt-2">
            Schedule information is clearly labeled and remains available when
            live data is unavailable.
          </p>
        </div>
        <Link
          className="bg-brand rounded-md px-4 py-2 font-semibold text-white"
          href="/health"
        >
          Service status
        </Link>
      </header>
      <section id="content" className="bg-surface rounded-xl border p-5">
        <label htmlFor="network-search" className="font-semibold">
          Search routes or stops
        </label>
        <input
          id="network-search"
          className="bg-canvas mt-2 w-full rounded-md border p-3"
          placeholder="Try Red Line or Harvard"
        />
        <p className="text-muted mt-2 text-sm">
          Search results use the scheduled MBTA feed.
        </p>
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <TransitMap routeName="Red Line" />
        <section id="stop-list" className="bg-surface rounded-xl border p-5">
          <h2 className="text-xl font-semibold">Red Line stop list</h2>
          <ol className="mt-4 divide-y">
            {stops.map((stop, index) => (
              <li key={stop} className="flex items-center justify-between py-3">
                <span>
                  <span className="text-muted mr-3 font-mono">{index + 1}</span>
                  {stop}
                </span>
                <Link
                  className="text-brand underline"
                  href={`/schedule/stops/${encodeURIComponent(stop)}`}
                >
                  View schedule
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </section>
      <section className="bg-surface rounded-xl border p-5">
        <h2 className="text-xl font-semibold">Scheduled departures</h2>
        <p className="text-muted mt-2">
          Scheduled · Service date July 24 · Times may differ during
          disruptions.
        </p>
        <ul className="mt-4 space-y-2">
          <li>Harvard → Alewife · 10:12 PM</li>
          <li>Harvard → Ashmont · 10:18 PM</li>
        </ul>
      </section>
    </main>
  );
}
