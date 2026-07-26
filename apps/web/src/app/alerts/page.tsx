import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/trust";
export default function AlertsPage() {
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">Agency notices</p>
        <h1 className="mt-1 text-3xl font-semibold">Service alerts</h1>
      </header>
      <div className="mt-6 space-y-4">
        <label className="font-semibold" htmlFor="alert-filter">
          Filter agency alerts
        </label>
        <input
          id="alert-filter"
          className="bg-surface border-border-strong min-h-11 w-full max-w-md rounded-md border px-3"
          placeholder="Route, stop, or effect"
        />
        <StatePanel kind="empty" title="No active alerts">
          When available, agency-provided notices will show their effect,
          affected routes, and source age.
        </StatePanel>
      </div>
    </AppShell>
  );
}
