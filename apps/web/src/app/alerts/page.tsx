import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/trust";
export default function AlertsPage() {
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">Agency notices</p>
        <h1 className="mt-1 text-3xl font-semibold">Service alerts</h1>
      </header>
      <div className="mt-6">
        <StatePanel kind="empty" title="No active alerts">
          When available, agency-provided notices will show their effect,
          affected routes, and source age.
        </StatePanel>
      </div>
    </AppShell>
  );
}
