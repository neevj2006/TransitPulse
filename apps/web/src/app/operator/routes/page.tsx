import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/trust";
export default function OperatorRoutesPage() {
  return (
    <AppShell operator>
      <h1 className="text-3xl font-semibold">Route diagnostics</h1>
      <div className="mt-6">
        <StatePanel kind="empty" title="No route diagnostics yet">
          Route comparisons will include coverage, sample size, and definition
          context.
        </StatePanel>
      </div>
    </AppShell>
  );
}
