import Link from "next/link";

export default function OfflinePage() {
  return (
    <main className="page-container">
      <section className="card max-w-xl">
        <h1 className="text-2xl font-semibold">You are offline</h1>
        <p className="text-muted mt-3">
          TransitPulse cannot retrieve live vehicle locations, predictions, or
          alerts until your connection returns. Any saved page is clearly
          separate from live data.
        </p>
        <Link
          className="text-brand mt-4 inline-flex min-h-11 items-center font-semibold underline"
          href="/"
        >
          Return home
        </Link>
      </section>
    </main>
  );
}
