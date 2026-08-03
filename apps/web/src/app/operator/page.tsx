import { AppShell } from "@/components/app-shell";
import { OperatorDashboard } from "@/components/operator-dashboard";
export default function OperatorPage() {
  return (
    <AppShell operator>
      <header>
        <p className="text-brand text-sm font-semibold">Operator workspace</p>
        <h1 className="mt-1 text-3xl font-semibold">System overview</h1>
        <p className="text-muted mt-2">
          Operational information is evidence-based and does not imply access
          control.
        </p>
      </header>
      <div className="mt-6">
        <OperatorDashboard view="overview" />
      </div>
    </AppShell>
  );
}
