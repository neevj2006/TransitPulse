import { AppShell } from "@/components/app-shell";
import { OperatorDashboard } from "@/components/operator-dashboard";
export default function OperatorSystemPage() {
  return (
    <AppShell operator>
      <h1 className="text-3xl font-semibold">System performance</h1>
      <div className="mt-6">
        <OperatorDashboard view="system" />
      </div>
    </AppShell>
  );
}
