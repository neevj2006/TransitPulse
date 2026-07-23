import type { Metadata } from "next";
import { CircleCheck, CircleHelp, Gauge } from "lucide-react";
import { StatusCard } from "@/components/status-card";
import { ThemeSelect } from "@/components/theme-select";
import { publicEnv } from "@/lib/env";

export const metadata: Metadata = {
  title: "Foundation health",
};

export default function HealthPage() {
  return (
    <>
      <a
        href="#main-content"
        className="bg-brand-strong fixed top-4 left-4 z-10 -translate-y-24 rounded-lg px-4 py-3 font-semibold text-white focus:translate-y-0"
      >
        Skip to main content
      </a>
      <header className="bg-surface border-b">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="bg-brand-soft text-brand-soft-text grid size-10 place-items-center rounded-xl">
              <Gauge aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="font-semibold tracking-tight">TransitPulse</p>
              <p className="text-muted text-sm">Foundation health</p>
            </div>
          </div>
          <ThemeSelect />
        </div>
      </header>
      <main
        id="main-content"
        className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
      >
        <section aria-labelledby="health-title" className="max-w-3xl">
          <p className="text-brand mb-3 text-sm font-semibold tracking-wider uppercase">
            Phase 2 foundation
          </p>
          <h1
            id="health-title"
            className="text-3xl font-semibold tracking-tight sm:text-4xl"
          >
            The web foundation is ready.
          </h1>
          <p className="text-muted mt-4 max-w-2xl text-base leading-7 sm:text-lg">
            This page exposes the current application version and environment
            without claiming transit data is available yet.
          </p>
        </section>

        <section
          aria-label="System status"
          className="mt-10 grid gap-4 md:grid-cols-3"
        >
          <StatusCard
            description="The Next.js application rendered successfully."
            icon={CircleCheck}
            label="Ready"
            tone="success"
            value="Web interface"
          />
          <StatusCard
            description="Validated at startup from the public environment contract."
            icon={CircleCheck}
            label="Configured"
            tone="success"
            value={publicEnv.NEXT_PUBLIC_APP_ENV}
          />
          <StatusCard
            description="Backend readiness is reported separately and is not inferred by this page."
            icon={CircleHelp}
            label="Unavailable"
            tone="unknown"
            value={`v${publicEnv.NEXT_PUBLIC_APP_VERSION}`}
          />
        </section>
      </main>
      <footer className="text-muted mx-auto mt-auto w-full max-w-6xl px-4 pb-8 text-sm sm:px-6 lg:px-8">
        Status uses explicit text and icons so meaning never depends on color.
      </footer>
    </>
  );
}
