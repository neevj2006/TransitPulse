import { AppShell } from "@/components/app-shell";
import { UniversalSearch } from "@/components/universal-search";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">Scheduled network</p>
        <h1 className="mt-1 text-3xl font-semibold">Search transit</h1>
        <p className="text-muted mt-2">
          Routes, stops, and destinations are matched from the published
          schedule.
        </p>
      </header>
      <section className="card mt-6 max-w-3xl">
        <UniversalSearch initialQuery={q} />
      </section>
    </AppShell>
  );
}
