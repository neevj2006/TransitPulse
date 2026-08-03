import { AppShell } from "@/components/app-shell";
import { OperatorDashboard } from "@/components/operator-dashboard";
export default function FeedHealthPage() {
  return (
    <AppShell operator>
      <h1 className="text-3xl font-semibold">Feed health</h1>
      <div className="mt-6">
        <OperatorDashboard view="feeds" />
      </div>
    </AppShell>
  );
}
