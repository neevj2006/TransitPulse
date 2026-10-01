import { AppShell } from "@/components/app-shell";
export default function AboutPage() {
  return (
    <AppShell>
      <h1 className="text-3xl font-bold">About TransitPulse</h1>
      <section className="card mt-6 space-y-4">
        <p>
          TransitPulse helps Boston riders distinguish schedules, agency
          predictions, historical evidence, and uncertainty. Operator views
          explain feed quality without claiming that missing data proves a
          service disruption.
        </p>
        <p>
          The public demonstration uses illustrative fixtures. A configured live
          installation reads MBTA feeds and retains bounded historical evidence.
          Neither mode guarantees arrivals or connections.
        </p>
        <a
          className="text-brand underline"
          href="https://github.com/neevj2006/TransitPulse"
        >
          Source code, local setup, and documented limitations
        </a>
      </section>
    </AppShell>
  );
}
