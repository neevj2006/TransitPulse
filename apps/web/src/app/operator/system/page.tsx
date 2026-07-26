import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/trust";
export default function OperatorSystemPage() {
  return (
    <AppShell operator>
      <h1 className="text-3xl font-semibold">System performance</h1>
      <div className="mt-6">
        <StatePanel kind="unknown" title="Performance metrics unavailable">
          Latency, connections, and availability will be shown from verified
          measurements.
        </StatePanel>
      </div>
    </AppShell>
  );
}
