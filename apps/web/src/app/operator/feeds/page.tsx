import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/trust";
export default function FeedHealthPage() {
  return (
    <AppShell operator>
      <h1 className="text-3xl font-semibold">Feed health</h1>
      <div className="mt-6">
        <StatePanel kind="unknown" title="No feed health data">
          A source age, last success, and recent failures will be shown when
          monitoring data is available.
        </StatePanel>
      </div>
    </AppShell>
  );
}
