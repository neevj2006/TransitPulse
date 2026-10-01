import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { UniversalSearch } from "@/components/universal-search";
export default function SchedulePage() {
  return (
    <AppShell>
      <h1 className="text-3xl font-bold">Find MBTA routes and stops</h1>
      <p className="text-muted mt-2">
        Search the available network. Arrival boards distinguish scheduled
        departures from fresh agency predictions.
      </p>
      <section className="card mt-6">
        <UniversalSearch />
      </section>
      <section className="card mt-6">
        <h2 className="text-xl font-semibold">Explore routes</h2>
        <ul className="mt-3 space-y-3">
          {["Red", "Orange", "Green-B"].map((route) => (
            <li key={route}>
              <Link className="text-brand underline" href={`/routes/${route}`}>
                {route} route and stops
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
