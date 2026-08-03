import { AppShell } from "@/components/app-shell";
import { OperatorDashboard } from "@/components/operator-dashboard";
export default function OperatorRoutesPage() {
  return (
    <AppShell operator>
      <h1 className="text-3xl font-semibold">Route diagnostics</h1>
      <div className="mt-6">
        <OperatorDashboard view="routes" />
      </div>
    </AppShell>
  );
}
