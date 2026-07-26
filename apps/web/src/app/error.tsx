"use client";
import { AppShell } from "@/components/app-shell";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <AppShell>
      <section className="card max-w-2xl">
        <h1 className="text-2xl font-semibold">We could not load this page</h1>
        <p className="text-muted mt-2">
          Try again. If the problem continues, use scheduled information where
          available.
        </p>
        <button
          type="button"
          onClick={reset}
          className="bg-brand-strong mt-5 min-h-11 rounded-md px-4 font-semibold text-white"
        >
          Try again
        </button>
      </section>
    </AppShell>
  );
}
