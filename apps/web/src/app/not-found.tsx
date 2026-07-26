import Link from "next/link";
import { AppShell } from "@/components/app-shell";
export default function NotFound() {
  return (
    <AppShell>
      <section className="card max-w-2xl">
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="text-muted mt-2">
          The route, stop, or page you requested is not available.
        </p>
        <Link
          className="text-brand mt-4 inline-block font-medium underline"
          href="/"
        >
          Return home
        </Link>
      </section>
    </AppShell>
  );
}
