import { AppShell } from "@/components/app-shell";
import { AccessibleLineChart } from "@/components/accessible-chart";
import { StatePanel } from "@/components/trust";
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
      <div className="mt-6 space-y-6">
        <AccessibleLineChart
          title="Delay trend"
          takeaway="A chart will show only retained observations, never an unsupported estimate."
          data={[]}
        />
        <StatePanel kind="empty" title="Not enough data yet">
          Historical reliability appears after sufficient observations are
          retained and validated.
        </StatePanel>
      </div>
    </AppShell>
  );
}
