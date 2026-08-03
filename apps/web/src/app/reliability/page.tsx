import { AppShell } from "@/components/app-shell";
import { ReliabilityDashboard } from "@/components/reliability-dashboard";
export default function ReliabilityPage() {
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">
          Historical performance
        </p>
        <h1 className="mt-1 text-3xl font-semibold">Reliability</h1>
        <p className="text-muted mt-2">
          Metrics include their coverage and sample size before they are
          presented.
        </p>
      </header>
      <ReliabilityDashboard />
    </AppShell>
  );
}
