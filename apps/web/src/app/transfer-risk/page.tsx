import { AppShell } from "@/components/app-shell";
import { TransferRiskCalculator } from "@/components/transfer-risk-calculator";

export default function TransferRiskPage() {
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">Connection planning</p>
        <h1 className="mt-1 text-3xl font-semibold">Transfer risk</h1>
        <p className="text-muted mt-2">
          Compare your planned buffer with historical delay evidence. It cannot
          guarantee a connection.
        </p>
      </header>
      <TransferRiskCalculator />
    </AppShell>
  );
}
